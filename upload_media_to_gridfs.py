#!/usr/bin/env python3
"""
Twitter Media Upload to MongoDB GridFS
=====================================
Uploads all Twitter media files from local filesystem to MongoDB GridFS for cloud storage.

Usage:
    python upload_media_to_gridfs.py [--config config_path] [--dry-run]

Features:
- Scans all twitter-scraper directories for media files
- Uploads to MongoDB GridFS with metadata
- Handles duplicates with MD5 hashing
- Updates tweet records with GridFS file IDs
- Progress reporting and statistics
- Dry-run mode for testing
"""

import os
import sys
import json
import hashlib
import mimetypes
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unified_app.twitter_mongo_manager import get_twitter_manager
from pymongo import MongoClient
from gridfs import GridFS
import gridfs


class MediaUploader:
    """
    Handles uploading Twitter media files from local filesystem to MongoDB GridFS.
    """
    
    def __init__(self, config_path: str = None, dry_run: bool = False):
        """
        Initialize the media uploader.
        
        Args:
            config_path: Path to MongoDB config file
            dry_run: If True, only show what would be uploaded without actually uploading
        """
        self.dry_run = dry_run
        self.stats = {
            'files_found': 0,
            'files_uploaded': 0,
            'files_skipped': 0,
            'files_failed': 0,
            'total_size_uploaded': 0,
            'duplicates_detected': 0
        }
        
        # Initialize MongoDB connection
        try:
            self.twitter_manager = get_twitter_manager(config_path)
            self.db = self.twitter_manager.db
            self.gridfs = self.twitter_manager.gridfs
            print(f"✅ Connected to MongoDB: {self.db.name}")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            sys.exit(1)
    
    def scan_media_files(self, base_path: str = "twitter-scraper") -> List[Dict]:
        """
        Scan for all media files in twitter-scraper directories.
        
        Args:
            base_path: Base directory to scan
            
        Returns:
            List of media file information
        """
        media_files = []
        base_dir = Path(base_path)
        
        if not base_dir.exists():
            print(f"❌ Directory not found: {base_path}")
            return media_files
        
        # Supported media extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.tif'}
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
        supported_extensions = image_extensions | video_extensions
        
        print(f"🔍 Scanning for media files in: {base_dir}")
        
        # Scan all subdirectories
        for subdir in base_dir.iterdir():
            if subdir.is_dir() and 'media_tweets' in subdir.name:
                media_dir = subdir
                print(f"  📁 Scanning: {media_dir}")
                
                # Find all media files
                for file_path in media_dir.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                        file_stat = file_path.stat()
                        
                        media_info = {
                            'file_path': str(file_path),
                            'relative_path': str(file_path.relative_to(base_dir)),
                            'filename': file_path.name,
                            'size': file_stat.st_size,
                            'extension': file_path.suffix.lower(),
                            'modified_time': file_stat.st_mtime,
                            'tweets_index_path': str(file_path.parent.parent / 'tweets_index.json'),
                            'tweets_folder': str(file_path.parent.parent)
                        }
                        
                        media_files.append(media_info)
                        self.stats['files_found'] += 1
        
        print(f"📊 Found {len(media_files)} media files")
        return media_files
    
    def upload_file_to_gridfs(self, media_info: Dict) -> Optional[str]:
        """
        Upload a single file to GridFS.
        
        Args:
            media_info: Media file information dictionary
            
        Returns:
            GridFS file ID if successful, None otherwise
        """
        try:
            file_path = media_info['file_path']
            
            if self.dry_run:
                print(f"  [DRY RUN] Would upload: {media_info['relative_path']} ({media_info['size']:,} bytes)")
                return "dry_run_id"
            
            # Check if file already exists in GridFS
            with open(file_path, 'rb') as f:
                content = f.read()
                file_hash = hashlib.md5(content).hexdigest()
            
            # Check for existing file
            existing_file = self.gridfs.find_one({"md5": file_hash})
            if existing_file:
                print(f"  ⏭️  Skipping (duplicate): {media_info['filename']}")
                self.stats['duplicates_detected'] += 1
                self.stats['files_skipped'] += 1
                return str(existing_file._id)
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Upload to GridFS
            with open(file_path, 'rb') as f:
                gridfs_id = self.gridfs.put(
                    f,
                    filename=media_info['filename'],
                    content_type=content_type,
                    upload_date=datetime.now(),
                    original_path=media_info['relative_path'],
                    file_size=media_info['size'],
                    media_type='video' if media_info['extension'] in {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'} else 'photo'
                )
            
            print(f"  ✅ Uploaded: {media_info['filename']} -> GridFS {gridfs_id}")
            self.stats['files_uploaded'] += 1
            self.stats['total_size_uploaded'] += media_info['size']
            
            return str(gridfs_id)
            
        except Exception as e:
            print(f"  ❌ Failed to upload {media_info['filename']}: {e}")
            self.stats['files_failed'] += 1
            return None
    
    def update_tweets_with_gridfs(self, tweets_folder: str, media_mappings: Dict[str, str]):
        """
        Update tweet records with GridFS file IDs.
        
        Args:
            tweets_folder: Path to tweets folder
            media_mappings: Mapping of original filenames to GridFS IDs
        """
        try:
            tweets_index_path = os.path.join(tweets_folder, 'tweets_index.json')
            
            if not os.path.exists(tweets_index_path):
                print(f"  ⚠️  No tweets index found: {tweets_index_path}")
                return
            
            with open(tweets_index_path, 'r', encoding='utf-8') as f:
                tweets_data = json.load(f)
            
            updated_count = 0
            for tweet in tweets_data:
                if tweet.get('has_media') and tweet.get('media_files'):
                    media_files = tweet.get('media_files', [])
                    gridfs_media = []
                    
                    for media_file in media_files:
                        original_filename = os.path.basename(media_file.get('file', ''))
                        
                        if original_filename in media_mappings:
                            gridfs_id = media_mappings[original_filename]
                            gridfs_media.append({
                                'gridfs_id': gridfs_id,
                                'type': media_file.get('type', 'photo'),
                                'original_filename': original_filename,
                                'size': media_file.get('size', 0)
                            })
                    
                    if gridfs_media:
                        # Update tweet with GridFS references
                        tweet['media_files_gridfs'] = gridfs_media
                        tweet['has_media_gridfs'] = True
                        updated_count += 1
            
            # Save updated tweets back to MongoDB
            if updated_count > 0 and not self.dry_run:
                self.twitter_manager.add_tweets_batch(tweets_data)
                print(f"  📝 Updated {updated_count} tweets with GridFS references")
            
        except Exception as e:
            print(f"  ❌ Failed to update tweets: {e}")
    
    def upload_all_media(self, base_path: str = "twitter-scraper") -> Dict:
        """
        Upload all media files from the specified directory.
        
        Args:
            base_path: Base directory containing twitter-scraper folders
            
        Returns:
            Dictionary with upload statistics
        """
        print("🚀 Starting media upload to MongoDB GridFS")
        print("=" * 50)
        
        if self.dry_run:
            print("🔍 DRY RUN MODE - No files will be uploaded")
            print("=" * 50)
        
        # Scan for media files
        media_files = self.scan_media_files(base_path)
        
        if not media_files:
            print("❌ No media files found to upload")
            return self.stats
        
        print(f"\n📋 Upload Summary:")
        print(f"   Files to process: {self.stats['files_found']}")
        print(f"   Total size: {sum(f['size'] for f in media_files):,} bytes")
        
        if not self.dry_run:
            print(f"   Estimated upload time: {self.stats['files_found'] * 2:.1f} seconds")
        
        print("\n" + "=" * 50)
        
        # Group media files by tweets folder for batch processing
        media_by_folder = {}
        for media_info in media_files:
            folder = media_info['tweets_folder']
            if folder not in media_by_folder:
                media_by_folder[folder] = []
            media_by_folder[folder].append(media_info)
        
        # Upload media files folder by folder
        for folder, folder_media in media_by_folder.items():
            print(f"\n📁 Processing folder: {os.path.basename(folder)}")
            
            # Upload files in this folder
            folder_mappings = {}
            for media_info in folder_media:
                gridfs_id = self.upload_file_to_gridfs(media_info)
                if gridfs_id:
                    folder_mappings[media_info['filename']] = gridfs_id
            
            # Update tweets with GridFS references
            if folder_mappings:
                self.update_tweets_with_gridfs(folder, folder_mappings)
        
        # Print final statistics
        print("\n" + "=" * 50)
        print("📊 Upload Complete!")
        print(f"   Files found: {self.stats['files_found']}")
        print(f"   Files uploaded: {self.stats['files_uploaded']}")
        print(f"   Files skipped: {self.stats['files_skipped']}")
        print(f"   Files failed: {self.stats['files_failed']}")
        print(f"   Duplicates detected: {self.stats['duplicates_detected']}")
        print(f"   Total size uploaded: {self.stats['total_size_uploaded']:,} bytes")
        
        if self.stats['total_size_uploaded'] > 0:
            print(f"   Upload size: {self.stats['total_size_uploaded'] / (1024*1024):.2f} MB")
        
        return self.stats


def main():
    """Main function to run the media uploader."""
    parser = argparse.ArgumentParser(description="Upload Twitter media files to MongoDB GridFS")
    parser.add_argument(
        "--config", 
        default="../config/mongodb_config.json",
        help="Path to MongoDB configuration file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading"
    )
    parser.add_argument(
        "--path",
        default="twitter-scraper",
        help="Base path to scan for media files"
    )
    
    args = parser.parse_args()
    
    # Validate config file
    if not os.path.exists(args.config):
        print(f"❌ Config file not found: {args.config}")
        print("   Please ensure your MongoDB config file exists")
        sys.exit(1)
    
    try:
        # Create and run uploader
        uploader = MediaUploader(config_path=args.config, dry_run=args.dry_run)
        uploader.upload_all_media(base_path=args.path)
        
    except KeyboardInterrupt:
        print("\n❌ Upload interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()