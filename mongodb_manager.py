import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, ConnectionFailure
import threading

# Setup logging
import os

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Check if running in production environment
DEBUG_MODE = os.getenv('DEBUG', 'False').lower() == 'true'

if DEBUG_MODE:
    # Development logging - console only
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
else:
    # Production logging - file + console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scraper.log'),
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger(__name__)


class MongoDBManager:
    """
    Crash-safe MongoDB database manager with duplicate detection and incremental saves.

    Features:
    - Atomic MongoDB operations (crash-safe by design)
    - URL-based duplicate detection with unique index
    - Separate collection for duplicate tracking
    - Thread-safe operations
    - Compatible interface with DatabaseManager (JSON version)
    """

    def __init__(self, config_path: str = None):
        """
        Initialize MongoDB connection with custom configuration.

        Args:
            config_path: Path to MongoDB configuration file
        """
        # Use environment variable if no config path provided
        if config_path is None:
            config_path = os.getenv('MONGODB_CONFIG_PATH', 'config/mongodb_config.json')
        
        self.config = self._load_config(config_path)
        self.lock = threading.Lock()

        # Connect to MongoDB
        try:
            self.client = MongoClient(
                self.config['connection_string'],
                serverSelectionTimeoutMS=5000
            )

            # Test connection
            self.client.server_info()
            logger.info(f"Connected to MongoDB at {self.config['connection_string']}")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

        # Get database and collections
        self.db = self.client[self.config['database_name']]
        self.articles_collection = self.db[self.config['collections']['articles']]
        self.scraper_runs_collection = self.db[self.config['collections']['scraper_runs']]
        self.seen_urls_collection = self.db[self.config['collections']['seen_urls']]
        self.stats_collection = self.db[self.config['collections']['stats']]

        # Create indexes for performance and uniqueness
        self._create_indexes()

        # Initialize stats document if it doesn't exist
        self._initialize_stats()

        logger.info(f"MongoDB Manager initialized with database: {self.config['database_name']}")

    def _load_config(self, config_path: str) -> Dict:
        """Load MongoDB configuration from JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise

    def _create_indexes(self):
        """Create indexes for performance and uniqueness."""
        # Unique index on URL to prevent duplicates in articles
        self.articles_collection.create_index([('url', ASCENDING)], unique=True)

        # Index on scraped_at for sorting
        self.articles_collection.create_index([('scraped_at', ASCENDING)])

        # Index on website_name for filtering
        self.articles_collection.create_index([('website_name', ASCENDING)])

        # Index for seen_urls collection - unique index on URL
        self.seen_urls_collection.create_index([('url', ASCENDING)], unique=True)
        self.seen_urls_collection.create_index([('first_seen', ASCENDING)])
        self.seen_urls_collection.create_index([('last_seen', ASCENDING)])

        # Index for scraper_runs collection
        self.scraper_runs_collection.create_index([('started_at', ASCENDING)])
        self.scraper_runs_collection.create_index([('status', ASCENDING)])

        logger.info("MongoDB indexes created successfully")

    def _initialize_stats(self):
        """Initialize stats document if it doesn't exist."""
        if self.stats_collection.count_documents({}) == 0:
            initial_stats = {
                'total_articles': 0,
                'total_duplicates': 0,
                'total_scraper_runs': 0,
                'last_updated': datetime.now().isoformat(),
                'sources': {}
            }
            self.stats_collection.insert_one(initial_stats)
            logger.info("Initialized stats document")

    def is_duplicate(self, url: str) -> bool:
        """
        Check if URL already exists in database (seen_urls collection).

        Args:
            url: Article URL to check

        Returns:
            True if URL exists, False otherwise
        """
        with self.lock:
            return self.seen_urls_collection.count_documents({'url': url}, limit=1) > 0

    def add_article(self, article: Dict, save_immediately: bool = True) -> Dict:
        """
        Add a single article to MongoDB database.

        MongoDB's insert operations are atomic by design, providing crash-safety.

        Args:
            article: Article data dictionary
            save_immediately: Kept for interface compatibility (MongoDB is always immediate)

        Returns:
            Dict with status information
        """
        url = article.get('url')

        if not url:
            logger.warning("Article missing URL, skipping")
            return {'status': 'error', 'reason': 'missing_url'}

        with self.lock:
            try:
                # Check if URL is in seen_urls (without acquiring lock again)
                is_dup = self.seen_urls_collection.count_documents({'url': url}, limit=1) > 0

                if is_dup:
                    logger.info(f"DUPLICATE FOUND: {url}")
                    self._track_duplicate(url, article.get('website_name'))
                    return {
                        'status': 'duplicate',
                        'url': url,
                        'message': 'Article already exists in database'
                    }

                # Add timestamp if not present
                if 'scraped_at' not in article:
                    article['scraped_at'] = datetime.now().isoformat()

                # Insert into MongoDB (atomic operation)
                result = self.articles_collection.insert_one(article)

                # Add URL to seen_urls collection
                self._add_to_seen_urls(url, article.get('website_name'))

                # Update stats
                self._update_stats(added=1, source=article.get('website_name'))

                total_articles = self.articles_collection.count_documents({})

                logger.info(f"✓ SAVED: {url[:80]}... (Total: {total_articles})")

                return {
                    'status': 'success',
                    'url': url,
                    'total_articles': total_articles,
                    'mongodb_id': str(result.inserted_id)
                }

            except DuplicateKeyError:
                # URL already exists (unique index violation in articles collection)
                logger.info(f"DUPLICATE FOUND: {url}")
                self._track_duplicate(url, article.get('website_name'))

                return {
                    'status': 'duplicate',
                    'url': url,
                    'message': 'Article already exists in database'
                }

            except Exception as e:
                logger.error(f"Error adding article: {e}")
                return {'status': 'error', 'reason': str(e)}

    def add_articles_batch(self, articles: List[Dict]) -> Dict:
        """
        Add multiple articles to MongoDB.

        Args:
            articles: List of article dictionaries

        Returns:
            Dict with summary statistics
        """
        results = {
            'total': len(articles),
            'added': 0,
            'duplicates': 0,
            'errors': 0,
            'duplicate_urls': []
        }

        for article in articles:
            result = self.add_article(article, save_immediately=True)

            if result['status'] == 'success':
                results['added'] += 1
            elif result['status'] == 'duplicate':
                results['duplicates'] += 1
                results['duplicate_urls'].append(result['url'])
            else:
                results['errors'] += 1

        logger.info(
            f"Batch complete: {results['added']} added, "
            f"{results['duplicates']} duplicates, {results['errors']} errors"
        )

        return results

    def _add_to_seen_urls(self, url: str, source: Optional[str] = None):
        """Add URL to seen_urls collection."""
        try:
            seen_entry = {
                'url': url,
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'source': source,
                'seen_count': 1
            }
            self.seen_urls_collection.insert_one(seen_entry)
        except DuplicateKeyError:
            # URL already in seen_urls, this shouldn't happen but handle it
            pass
        except Exception as e:
            logger.error(f"Error adding to seen_urls: {e}")

    def _track_duplicate(self, url: str, source: Optional[str] = None):
        """Track duplicate URL encounters."""
        try:
            # Update seen_urls with new encounter
            self.seen_urls_collection.update_one(
                {'url': url},
                {
                    '$set': {'last_seen': datetime.now().isoformat()},
                    '$inc': {'seen_count': 1}
                }
            )

            # Update stats
            self._update_stats(duplicates=1)

        except Exception as e:
            logger.error(f"Error tracking duplicate: {e}")

    def _update_stats(self, added: int = 0, duplicates: int = 0, source: Optional[str] = None):
        """Update the stats collection."""
        try:
            update_dict = {
                '$inc': {},
                '$set': {'last_updated': datetime.now().isoformat()}
            }

            if added > 0:
                update_dict['$inc']['total_articles'] = added
            if duplicates > 0:
                update_dict['$inc']['total_duplicates'] = duplicates

            # Update source-specific stats
            if source and added > 0:
                update_dict['$inc'][f'sources.{source}.articles'] = added
            if source and duplicates > 0:
                update_dict['$inc'][f'sources.{source}.duplicates'] = duplicates

            self.stats_collection.update_one({}, update_dict, upsert=True)

        except Exception as e:
            logger.error(f"Error updating stats: {e}")

    def get_all_articles(self) -> List[Dict]:
        """
        Get all articles from MongoDB database.

        Returns:
            List of article dictionaries
        """
        with self.lock:
            articles = list(self.articles_collection.find({}, {'_id': 0}))
            return articles

    def get_all_articles_sorted(self) -> List[Dict]:
        """
        Get all articles from MongoDB database, sorted by scraped_at in descending order.

        Returns:
            List of article dictionaries, sorted newest first
        """
        with self.lock:
            articles = list(self.articles_collection.find(
                {},
                {'_id': 0}
            ).sort('scraped_at', -1))  # -1 for descending order
            return articles

    def get_article_by_id(self, article_id: str) -> Optional[Dict]:
        """
        Get a single article by its URL (which serves as the ID).

        Args:
            article_id: Article URL (used as ID)

        Returns:
            Article dictionary or None if not found
        """
        with self.lock:
            article = self.articles_collection.find_one({'url': article_id}, {'_id': 0})
            return article

    def get_database_stats(self) -> Dict:
        """
        Get database statistics from stats collection.

        Returns:
            Dict with statistics
        """
        with self.lock:
            # Get stats from stats collection
            stats_doc = self.stats_collection.find_one({}, {'_id': 0})

            if not stats_doc:
                # Fallback to counting if stats doc doesn't exist
                stats_doc = {
                    'total_articles': self.articles_collection.count_documents({}),
                    'total_duplicates': 0,
                    'last_updated': datetime.now().isoformat()
                }

            # Get actual counts
            total_articles = self.articles_collection.count_documents({})
            total_seen_urls = self.seen_urls_collection.count_documents({})
            total_scraper_runs = self.scraper_runs_collection.count_documents({})

            # Get last updated timestamp
            last_article = self.articles_collection.find_one(
                {},
                {'scraped_at': 1},
                sort=[('scraped_at', -1)]
            )

            last_updated = last_article.get('scraped_at') if last_article else None

            # Get database size
            db_stats = self.db.command('dbStats')

            return {
                'total_articles': total_articles,
                'total_seen_urls': total_seen_urls,
                'total_duplicates': stats_doc.get('total_duplicates', 0),
                'total_scraper_runs': total_scraper_runs,
                'last_updated': last_updated,
                'database_size_bytes': db_stats.get('dataSize', 0),
                'storage_engine': 'MongoDB Atlas',
                'connection_string': self.config['connection_string'].split('@')[1] if '@' in self.config['connection_string'] else self.config['connection_string'],
                'sources': stats_doc.get('sources', {})
            }

    def get_seen_urls(self) -> List[Dict]:
        """
        Get all seen URLs with metadata.

        Returns:
            List of seen URL dictionaries
        """
        with self.lock:
            seen_urls = list(self.seen_urls_collection.find({}, {'_id': 0}))
            return seen_urls

    def get_duplicates(self) -> List[Dict]:
        """
        Get all URLs that have been seen more than once (duplicates).

        Returns:
            List of duplicate URL dictionaries
        """
        with self.lock:
            duplicates = list(self.seen_urls_collection.find(
                {'seen_count': {'$gt': 1}},
                {'_id': 0}
            ))
            return duplicates

    def start_scraper_run(self, source: Optional[str] = None) -> str:
        """
        Start a new scraper run and return its ID.

        Args:
            source: Source being scraped

        Returns:
            Scraper run ID (string)
        """
        with self.lock:
            run_doc = {
                'started_at': datetime.now().isoformat(),
                'status': 'running',
                'source': source,
                'articles_scraped': 0,
                'duplicates_found': 0,
                'errors': 0
            }
            result = self.scraper_runs_collection.insert_one(run_doc)

            # Update stats
            self.stats_collection.update_one(
                {},
                {'$inc': {'total_scraper_runs': 1}},
                upsert=True
            )

            run_id = str(result.inserted_id)
            logger.info(f"Started scraper run: {run_id}")
            return run_id

    def update_scraper_run(self, run_id: str, articles: int = 0, duplicates: int = 0, errors: int = 0, status: Optional[str] = None):
        """
        Update scraper run statistics.

        Args:
            run_id: Scraper run ID
            articles: Number of articles scraped
            duplicates: Number of duplicates found
            errors: Number of errors
            status: New status (optional)
        """
        from bson.objectid import ObjectId

        with self.lock:
            update_dict = {'$inc': {}}

            if articles > 0:
                update_dict['$inc']['articles_scraped'] = articles
            if duplicates > 0:
                update_dict['$inc']['duplicates_found'] = duplicates
            if errors > 0:
                update_dict['$inc']['errors'] = errors

            if status:
                update_dict['$set'] = {'status': status}

            self.scraper_runs_collection.update_one(
                {'_id': ObjectId(run_id)},
                update_dict
            )

    def end_scraper_run(self, run_id: str, status: str = 'completed'):
        """
        Mark a scraper run as completed.

        Args:
            run_id: Scraper run ID
            status: Final status (completed, failed, etc.)
        """
        from bson.objectid import ObjectId

        with self.lock:
            self.scraper_runs_collection.update_one(
                {'_id': ObjectId(run_id)},
                {
                    '$set': {
                        'status': status,
                        'ended_at': datetime.now().isoformat()
                    }
                }
            )
            logger.info(f"Ended scraper run {run_id} with status: {status}")

    def get_scraper_runs(self, limit: int = 10) -> List[Dict]:
        """
        Get recent scraper runs.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of scraper run dictionaries
        """
        with self.lock:
            runs = list(self.scraper_runs_collection.find(
                {},
                {'_id': 0}
            ).sort('started_at', -1).limit(limit))
            return runs

    def backup_database(self, backup_dir: str = 'data/backups') -> str:
        """
        Create a JSON backup of MongoDB data.

        Args:
            backup_dir: Directory to store backup

        Returns:
            Path to backup file
        """
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f'mongodb_backup_{timestamp}.json')

        with self.lock:
            # Get articles without calling get_all_articles (to avoid lock recursion)
            articles = list(self.articles_collection.find({}, {'_id': 0}))

            backup_data = {
                'metadata': {
                    'backup_created_at': datetime.now().isoformat(),
                    'total_articles': len(articles),
                    'source': 'MongoDB',
                    'database': self.config['database_name']
                },
                'articles': articles
            }

            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

        logger.info(f"MongoDB database backed up to {backup_path}")
        return backup_path

    def merge_old_json_files(self, output_dir: str = 'output') -> Dict:
        """
        Merge all existing JSON files from output directory into MongoDB.

        Args:
            output_dir: Directory containing old JSON files

        Returns:
            Dict with merge statistics
        """
        stats = {
            'files_processed': 0,
            'articles_added': 0,
            'duplicates_found': 0
        }

        # Find all JSON files
        json_files = []
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                if filename.endswith('.json') and 'scraped_articles' in filename:
                    json_files.append(os.path.join(output_dir, filename))

        logger.info(f"Found {len(json_files)} JSON files to merge into MongoDB")

        for filepath in json_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    articles = json.load(f)

                # Handle both list format and dict format
                if isinstance(articles, dict):
                    articles = articles.get('articles', [])

                result = self.add_articles_batch(articles)

                stats['files_processed'] += 1
                stats['articles_added'] += result['added']
                stats['duplicates_found'] += result['duplicates']

                logger.info(f"Merged {filepath}: {result['added']} new, {result['duplicates']} duplicates")

            except Exception as e:
                logger.error(f"Error merging {filepath}: {e}")

        logger.info(
            f"Merge complete: {stats['files_processed']} files, "
            f"{stats['articles_added']} articles added, "
            f"{stats['duplicates_found']} duplicates"
        )

        return stats

    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


# Singleton instance
_mongodb_manager_instance = None
_instance_lock = threading.Lock()


def get_mongodb_manager(config_path: str = 'config/mongodb_config.json') -> MongoDBManager:
    """
    Get singleton instance of MongoDBManager.

    Args:
        config_path: Path to MongoDB configuration file

    Returns:
        MongoDBManager instance
    """
    global _mongodb_manager_instance

    if _mongodb_manager_instance is None:
        with _instance_lock:
            if _mongodb_manager_instance is None:
                _mongodb_manager_instance = MongoDBManager(config_path)

    return _mongodb_manager_instance
