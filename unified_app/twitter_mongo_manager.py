"""
Twitter MongoDB Manager
Handles storage and retrieval of Twitter data in MongoDB Atlas
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson import ObjectId
from gridfs import GridFS
import gridfs
import hashlib
import mimetypes
import threading

logger = logging.getLogger(__name__)


class TwitterMongoManager:
    """
    MongoDB manager for Twitter data with support for:
    - Tweet storage with media references
    - User management
    - Keyword search history
    - Duplicate detection
    """

    def __init__(self, config_path: str = None):
        """Initialize MongoDB connection for Twitter data."""
        # Use environment variable if no config path provided
        if config_path is None:
            config_path = os.getenv('MONGODB_CONFIG_PATH', '../config/mongodb_config.json')
        
        self.config = self._load_config(config_path)
        self.lock = threading.Lock()

        # Connect to MongoDB
        try:
            # Simple connection - let pymongo handle SSL automatically
            self.client = MongoClient(
                self.config['connection_string'],
                serverSelectionTimeoutMS=30000
            )
            self.client.server_info()
            logger.info(f"Twitter MongoDB Manager connected to {self.config['connection_string']}")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

        # Get database and collections
        self.db = self.client[self.config['database_name']]
        self.tweets_collection = self.db['tweets']
        self.twitter_users_collection = self.db['twitter_users']
        self.twitter_stats_collection = self.db['twitter_stats']

        # Initialize GridFS for media storage
        self.gridfs = GridFS(self.db)

        # Create indexes
        self._create_indexes()
        self._initialize_stats()

        logger.info("Twitter MongoDB Manager initialized")

    def _load_config(self, config_path: str) -> Dict:
        """Load MongoDB configuration from JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            raise

    def _create_indexes(self):
        """Create indexes for Twitter collections."""
        # Unique index on tweet ID
        self.tweets_collection.create_index([('tweet_id', ASCENDING)], unique=True)
        self.tweets_collection.create_index([('date', DESCENDING)])
        self.tweets_collection.create_index([('username', ASCENDING)])
        self.tweets_collection.create_index([('type', ASCENDING)])
        self.tweets_collection.create_index([('keyword', ASCENDING)])

        # Index for users collection
        self.twitter_users_collection.create_index([('username', ASCENDING)], unique=True)

        logger.info("Twitter MongoDB indexes created")

    def _initialize_stats(self):
        """Initialize Twitter stats document if it doesn't exist."""
        if self.twitter_stats_collection.count_documents({}) == 0:
            initial_stats = {
                'total_tweets': 0,
                'total_users': 0,
                'total_keywords_searches': 0,
                'last_updated': datetime.now().isoformat(),
                'users': {},
                'keywords': {}
            }
            self.twitter_stats_collection.insert_one(initial_stats)
            logger.info("Initialized Twitter stats document")

    def add_tweet(self, tweet: Dict) -> Dict:
        """
        Add a tweet to MongoDB.

        Args:
            tweet: Tweet data dictionary

        Returns:
            Dict with status information
        """
        tweet_id = tweet.get('tweet_id') or tweet.get('id')

        if not tweet_id:
            logger.warning("Tweet missing ID, skipping")
            return {'status': 'error', 'reason': 'missing_id'}

        with self.lock:
            try:
                # Add scraped_at timestamp if not present
                if 'scraped_at' not in tweet:
                    tweet['scraped_at'] = datetime.now().isoformat()

                # Ensure tweet_id field exists
                tweet['tweet_id'] = tweet_id

                # Store media files in GridFS if present
                if tweet.get('has_media') and tweet.get('media_files'):
                    tweet = self.store_media_for_tweet(tweet)
                    logger.info(f"Stored media files for tweet {tweet_id} in GridFS")

                # Insert into MongoDB
                result = self.tweets_collection.insert_one(tweet)

                # Update stats
                self._update_stats(
                    tweets=1,
                    username=tweet.get('username') or tweet.get('original_author'),
                    keyword=tweet.get('keyword')
                )

                total_tweets = self.tweets_collection.count_documents({})
                media_count = len(tweet.get('media_files_gridfs', []))

                logger.info(f"✓ SAVED TWEET: {tweet_id} with {media_count} media files (Total: {total_tweets})")

                return {
                    'status': 'success',
                    'tweet_id': tweet_id,
                    'total_tweets': total_tweets,
                    'media_files_stored': media_count,
                    'mongodb_id': str(result.inserted_id)
                }

            except DuplicateKeyError:
                logger.info(f"DUPLICATE TWEET: {tweet_id}")
                return {
                    'status': 'duplicate',
                    'tweet_id': tweet_id,
                    'message': 'Tweet already exists in database'
                }

            except Exception as e:
                logger.error(f"Error adding tweet: {e}")
                return {'status': 'error', 'reason': str(e)}

    def add_tweets_batch(self, tweets: List[Dict]) -> Dict:
        """
        Add multiple tweets to MongoDB.

        Args:
            tweets: List of tweet dictionaries

        Returns:
            Dict with summary statistics
        """
        results = {
            'total': len(tweets),
            'added': 0,
            'duplicates': 0,
            'errors': 0
        }

        for tweet in tweets:
            result = self.add_tweet(tweet)

            if result['status'] == 'success':
                results['added'] += 1
            elif result['status'] == 'duplicate':
                results['duplicates'] += 1
            else:
                results['errors'] += 1

        logger.info(
            f"Batch complete: {results['added']} added, "
            f"{results['duplicates']} duplicates, {results['errors']} errors"
        )

        return results

    def get_tweets(self, username: Optional[str] = None, keyword: Optional[str] = None,
                   limit: int = 100, skip: int = 0) -> List[Dict]:
        """
        Get tweets with optional filtering.

        Args:
            username: Filter by username
            keyword: Filter by keyword
            limit: Maximum number of tweets
            skip: Number of tweets to skip (pagination)

        Returns:
            List of tweets
        """
        with self.lock:
            query = {}

            if username:
                query['username'] = username
            if keyword:
                query['keyword'] = keyword

            tweets = list(self.tweets_collection.find(
                query,
                {'_id': 0}
            ).sort('date', DESCENDING).skip(skip).limit(limit))

            return tweets

    def search_tweets(self, search_term: str, limit: int = 100) -> List[Dict]:
        """
        Search tweets by text content.

        Args:
            search_term: Search term
            limit: Maximum results

        Returns:
            List of matching tweets
        """
        with self.lock:
            tweets = list(self.tweets_collection.find(
                {'$text': {'$search': search_term}},
                {'_id': 0}
            ).limit(limit))

            return tweets

    def get_all_tweets(self) -> List[Dict]:
        """Get all tweets from database."""
        with self.lock:
            tweets = list(self.tweets_collection.find({}, {'_id': 0}).sort('date', DESCENDING))
            return tweets

    def add_user(self, username: str, display_name: Optional[str] = None) -> Dict:
        """
        Add a Twitter user to track.

        Args:
            username: Twitter username
            display_name: Display name

        Returns:
            Dict with status
        """
        with self.lock:
            try:
                user_doc = {
                    'username': username,
                    'display_name': display_name or username,
                    'added_at': datetime.now().isoformat(),
                    'total_tweets': 0,
                    'last_scraped': None
                }

                self.twitter_users_collection.insert_one(user_doc)

                # Update stats
                self.twitter_stats_collection.update_one(
                    {},
                    {'$inc': {'total_users': 1}},
                    upsert=True
                )

                logger.info(f"Added user: @{username}")

                return {'status': 'success', 'username': username}

            except DuplicateKeyError:
                return {'status': 'duplicate', 'message': 'User already exists'}

            except Exception as e:
                logger.error(f"Error adding user: {e}")
                return {'status': 'error', 'reason': str(e)}

    def get_users(self) -> List[Dict]:
        """Get all tracked users."""
        with self.lock:
            users = list(self.twitter_users_collection.find({}, {'_id': 0}))
            return users

    def remove_user(self, username: str) -> Dict:
        """Remove a user from tracking."""
        with self.lock:
            result = self.twitter_users_collection.delete_one({'username': username})

            if result.deleted_count > 0:
                self.twitter_stats_collection.update_one(
                    {},
                    {'$inc': {'total_users': -1}}
                )
                logger.info(f"Removed user: @{username}")
                return {'status': 'success'}
            else:
                return {'status': 'not_found'}

    def _update_stats(self, tweets: int = 0, username: Optional[str] = None,
                      keyword: Optional[str] = None):
        """Update Twitter statistics."""
        try:
            update_dict = {
                '$inc': {},
                '$set': {'last_updated': datetime.now().isoformat()}
            }

            if tweets > 0:
                update_dict['$inc']['total_tweets'] = tweets

            if username:
                update_dict['$inc'][f'users.{username}.tweets'] = tweets

            if keyword:
                update_dict['$inc'][f'keywords.{keyword}.tweets'] = tweets
                update_dict['$inc']['total_keywords_searches'] = 1

            self.twitter_stats_collection.update_one({}, update_dict, upsert=True)

        except Exception as e:
            logger.error(f"Error updating stats: {e}")

    def get_stats(self) -> Dict:
        """Get Twitter statistics."""
        with self.lock:
            stats_doc = self.twitter_stats_collection.find_one({}, {'_id': 0})

            if not stats_doc:
                stats_doc = {
                    'total_tweets': 0,
                    'total_users': 0,
                    'last_updated': datetime.now().isoformat()
                }

            # Get actual counts
            stats_doc['total_tweets'] = self.tweets_collection.count_documents({})
            stats_doc['total_users'] = self.twitter_users_collection.count_documents({})

            return stats_doc

    def upload_media_file(self, file_path: str, tweet_id: str, media_type: str = 'photo') -> Optional[str]:
        """
        Upload a media file to GridFS.
        
        Args:
            file_path: Path to the media file
            tweet_id: ID of the tweet this media belongs to
            media_type: Type of media (photo, video, gif)
            
        Returns:
            GridFS file ID if successful, None otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"Media file not found: {file_path}")
                return None
                
            # Create unique filename with tweet ID
            filename = os.path.basename(file_path)
            gridfs_filename = f"{tweet_id}_{filename}"
            
            # Get file content and metadata
            with open(file_path, 'rb') as f:
                content = f.read()
                
            # Calculate file hash for deduplication
            file_hash = hashlib.md5(content).hexdigest()
            
            # Check if file already exists
            existing_file = self.gridfs.find_one({"md5": file_hash})
            if existing_file:
                logger.info(f"Media file already exists in GridFS: {gridfs_filename}")
                return str(existing_file._id)
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Upload to GridFS
            file_id = self.gridfs.put(
                content,
                filename=gridfs_filename,
                content_type=content_type,
                tweet_id=tweet_id,
                original_filename=filename,
                upload_date=datetime.now(),
                media_type=media_type
            )
            
            logger.info(f"Uploaded media to GridFS: {gridfs_filename} (ID: {file_id})")
            return str(file_id)
            
        except Exception as e:
            logger.error(f"Error uploading media file {file_path}: {e}")
            return None

    def get_media_file(self, gridfs_id: str) -> Optional[Dict]:
        """
        Retrieve a media file from GridFS.

        Args:
            gridfs_id: GridFS file ID

        Returns:
            Dict with file content and metadata, None if not found
        """
        try:
            file_obj = self.gridfs.get(ObjectId(gridfs_id))
            
            return {
                'content': file_obj.read(),
                'filename': file_obj.filename,
                'content_type': file_obj.content_type,
                'length': file_obj.length,
                'upload_date': file_obj.upload_date
            }
            
        except Exception as e:
            logger.error(f"Error retrieving media file {gridfs_id}: {e}")
            return None

    def store_media_for_tweet(self, tweet: Dict) -> Dict:
        """
        Process and store media files for a tweet in GridFS.
        
        Args:
            tweet: Tweet dictionary with media file references
            
        Returns:
            Updated tweet dictionary with GridFS file IDs
        """
        tweet_id = tweet.get('tweet_id')
        if not tweet_id:
            return tweet
            
        media_files = tweet.get('media_files', [])
        stored_media = []
        
        for media_file in media_files:
            local_path = media_file.get('file', '')
            
            # Convert local path to GridFS ID
            if local_path:
                gridfs_id = self.upload_media_file(
                    local_path,
                    tweet_id,
                    media_file.get('type', 'photo')
                )
                
                if gridfs_id:
                    # Update media file with GridFS reference
                    stored_media.append({
                        'gridfs_id': gridfs_id,
                        'type': media_file.get('type', 'photo'),
                        'original_filename': os.path.basename(local_path),
                        'size': media_file.get('size', 0)
                    })
                    
                    logger.info(f"Stored media for tweet {tweet_id}: {media_file.get('file')} -> GridFS {gridfs_id}")
        
        # Update tweet with GridFS media references
        tweet['media_files_gridfs'] = stored_media
        tweet['has_media_gridfs'] = len(stored_media) > 0
        
        return tweet

    def serve_media_from_gridfs(self, gridfs_id: str):
        """
        Serve media file directly from GridFS via Flask response.

        Args:
            gridfs_id: GridFS file ID

        Returns:
            Flask response with media content
        """
        try:
            from flask import Response

            file_data = self.get_media_file(gridfs_id)
            if not file_data:
                return None
                
            return Response(
                file_data['content'],
                mimetype=file_data['content_type'],
                headers={
                    'Content-Disposition': f'inline; filename="{file_data["filename"]}"'
                }
            )
            
        except Exception as e:
            logger.error(f"Error serving media from GridFS {gridfs_id}: {e}")
            return None


# Singleton instance
_twitter_manager_instance = None
_instance_lock = threading.Lock()


def get_twitter_manager(config_path: str = '../config/mongodb_config.json') -> TwitterMongoManager:
    """Get singleton instance of TwitterMongoManager."""
    global _twitter_manager_instance

    if _twitter_manager_instance is None:
        with _instance_lock:
            if _twitter_manager_instance is None:
                _twitter_manager_instance = TwitterMongoManager(config_path)

    return _twitter_manager_instance
