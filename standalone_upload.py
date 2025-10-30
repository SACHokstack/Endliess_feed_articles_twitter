#!/usr/bin/env python3
"""
Standalone Twitter Media Upload to MongoDB GridFS
================================================
Simple standalone script to upload Twitter media from local laptop to MongoDB.

This version has no dependencies on the main project - just pure GridFS upload.

Requirements:
- pip install pymongo gridfs
- MongoDB Atlas connection string
- Local twitter-scraper directories with media files

Usage:
    python standalone_upload.py [--connection-string "mongodb+srv://..."] [--dry-run]

No additional configuration files needed!
"""

import os
import sys
import json
import hashlib
import mimetypes
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import DuplicateKeyError, ConnectionFailure
    from gridfs import GridFS
    import gridfs
except ImportError:
    print("❌ Error: pymongo and gridfs are required.")
    print("   Install with: pip install pymongo gridfs")
    sys.exit(1)


class SimpleMediaUploader:
    """Simplified media uploader with minimal dependencies."""
    
    def __init__(self, connection_string: str, database_name: str = "Beautiful_Spine", dry_run: bool = False):
        """
        Initialize uploader with direct MongoDB connection.
        
        Args:
            connection_string: MongoDB Atlas connection string
            database_name: Database name
            dry_run: If True, only show what would be uploaded
        """
        self.dry_run = dry_run
        self.database_name = database_name
        self.stats = {
            'files_found': 0,
            'files_uploaded': 0,
            'files_skipped': 0,
            'files_failed': 0,
            'total_size_uploaded': 0,
            'duplicates_detected': 0
        }
        
        # Connect to MongoDB
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.client.server_info()
            self.db = self.client[database_name]
            self.gridfs = GridFS(self.db)
            print(f"✅ Connected to MongoDB: {database_name}")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            sys.exit(1)
    
    def scan_media_files(self, base_path: str = "twitter-scraper") -> List[Dict]:
        """Scan for media files in twitter-scraper directories."""
        media_files = []
        base_dir = Path(base_path)
        
        if not base_dir.exists():
            print(f"❌ Directory not found: {base_path}")
            return media_files
        
        # Supported media extensions
        supported_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.tif',
                               '.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
        
        print(f"🔍 Scanning for media files in: {base_dir}")
        
        # Find all media directories
        for subdir in base_dir.iterdir():
            if subdir.is_dir():
                media_dir = subdir / "media_tweets"
                if media_dir.exists():
                    print(f"  📁 Scanning: {media_dir}")
                    
                    # Find all media files
                    for file_path in media_dir.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                            file_stat = file_path.stat()
                            
                            media_info = {
                                'file_path': str(file_path),
                                'filename': file_path.name,
                                'size': file_stat.st_size,
                                'extension': file_path.suffix.lower(),
                                'folder_name': subdir.name
                            }
                            
                            media_files.append(media_info)
                            self.stats['files_found'] += 1
        
        print(f"📊 Found {len(media_files)} media files")
        return media_files
    
    def upload_file_to_gridfs(self, media_info: Dict) -> Optional[str]:
        """Upload a single file to GridFS."""
        try:
            file_path = media_info['file_path']
            filename = media_info['filename']
            
            if self.dry_run:
                print(f"  [DRY RUN] Would upload: {filename} ({media_info['size']:,} bytes)")
                return "dry_run_id"
            
            # Calculate file hash for deduplication
            with open(file_path, 'rb') as f:
                content = f.read()
                file_hash = hashlib.md5(content).hexdigest()
            
            # Check for existing file
            existing_file = self.gridfs.find_one({"md5": file_hash})
            if existing_file:
                print(f"  ⏭️  Skipping (duplicate): {filename}")
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
                    filename=filename,
                    content_type=content_type,
                    upload_date=datetime.now(),
                    original_path=media_info['folder_name'],
                    file_size=media_info['size'],
                    media_type='video' if media_info['extension'] in {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'} else 'photo'
                )
            
            print(f"  ✅ Uploaded: {filename} -> GridFS {gridfs_id}")
            self.stats['files_uploaded'] += 1
            self.stats['total_size_uploaded'] += media_info['size']
            
            return str(gridfs_id)
            
        except Exception as e:
            print(f"  ❌ Failed to upload {media_info['filename']}: {e}")
            self.stats['files_failed'] += 1
            return None
    
    def upload_all_media(self, base_path: str = "twitter-scraper") -> Dict:
        """Upload all media files."""
        print("🚀 Starting media upload to MongoDB GridFS (Standalone Mode)")
        print("=" * 60)
        
        if self.dry_run:
            print("🔍 DRY RUN MODE - No files will be uploaded")
            print("=" * 60)
        
        # Scan for media files
        media_files = self.scan_media_files(base_path)
        
        if not media_files:
            print("❌ No media files found to upload")
            return self.stats
        
        # Calculate total size
        total_size = sum(f['size'] for f in media_files)
        print(f"\n📋 Upload Summary:")
        print(f"   Files to process: {self.stats['files_found']}")
        print(f"   Total size: {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)")
        
        if not self.dry_run:
            estimated_time = self.stats['files_found'] * 2
            print(f"   Estimated upload time: {estimated_time:.1f} seconds")
        
        print("\n" + "=" * 60)
        
        # Upload files
        for i, media_info in enumerate(media_files, 1):
            print(f"[{i}/{len(media_files)}] Processing: {media_info['filename']}")
            self.upload_file_to_gridfs(media_info)
        
        # Print final statistics
        print("\n" + "=" * 60)
        print("📊 Upload Complete!")
        print(f"   Files found: {self.stats['files_found']}")
        print(f"   Files uploaded: {self.stats['files_uploaded']}")
        print(f"   Files skipped: {self.stats['files_skipped']}")
        print(f"   Files failed: {self.stats['files_failed']}")
        print(f"   Duplicates detected: {self.stats['duplicates_detected']}")
        print(f"   Total size uploaded: {self.stats['total_size_uploaded']:,} bytes")
        
        if self.stats['total_size_uploaded'] > 0:
            size_mb = self.stats['total_size_uploaded'] / (1024*1024)
            print(f"   Upload size: {size_mb:.2f} MB")
        
        return self.stats


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Upload Twitter media files to MongoDB GridFS (Standalone)")
    parser.add_argument(
        "--connection-string",
        default="mongodb+srv://sachivcsv_db_user:tfLNVtw5PlMOFxI7@cluster0.sez8ihw.mongodb.net/spine_scraper",
        help="MongoDB Atlas connection string"
    )
    parser.add_argument(
        "--database",
        default="Beautiful_Spine",
        help="Database name"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading"
    )
    parser.add_argument(
        "--path",
        default="twitter-scraper",
        help="Path to twitter-scraper directory"
    )
    
    args = parser.parse_args()
    
    try:
        print("📋 Configuration:")
        print(f"   Connection: {args.connection_string.split('@')[1] if '@' in args.connection_string else 'local'}")
        print(f"   Database: {args.database}")
        print(f"   Path: {args.path}")
        print(f"   Dry run: {args.dry_run}")
        print()
        
        # Create and run uploader
        uploader = SimpleMediaUploader(
            connection_string=args.connection_string,
            database_name=args.database,
            dry_run=args.dry_run
        )
        uploader.upload_all_media(base_path=args.path)
        
    except KeyboardInterrupt:
        print("\n❌ Upload interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()