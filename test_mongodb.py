#!/usr/bin/env python3
"""
Test script for MongoDB connection and operations.
Run this to verify MongoDB is set up correctly before migration.
"""

import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_mongodb_connection():
    """Test basic MongoDB connection."""
    print("="*80)
    print("MONGODB CONNECTION TEST")
    print("="*80 + "\n")

    try:
        print("1. Importing MongoDB manager...")
        from mongodb_manager import get_mongodb_manager
        print("   ✓ Import successful\n")

        print("2. Connecting to MongoDB...")
        db = get_mongodb_manager()
        print(f"   ✓ Connected to {db.config['connection_string']}")
        print(f"   Database: {db.config['database_name']}\n")

        print("3. Testing database operations...\n")

        # Test 1: Get initial stats
        print("   Test 1: Get database statistics")
        stats = db.get_database_stats()
        print(f"   ✓ Total articles: {stats['total_articles']}")
        print(f"   ✓ Total seen URLs: {stats['total_seen_urls']}")
        print(f"   ✓ Total duplicates: {stats['total_duplicates']}")
        print(f"   ✓ Total scraper runs: {stats['total_scraper_runs']}")
        print(f"   ✓ Storage engine: {stats['storage_engine']}\n")

        # Test 2: Add a test article
        print("   Test 2: Add test article")
        test_article = {
            'title': 'MongoDB Test Article',
            'url': f'https://test.example.com/mongodb-test-{datetime.now().timestamp()}',
            'website_name': 'Test Source',
            'content': 'This is a test article for MongoDB',
            'scraped_at': datetime.now().isoformat()
        }

        result = db.add_article(test_article, save_immediately=True)

        if result['status'] == 'success':
            print(f"   ✓ Article added successfully")
            print(f"   MongoDB ID: {result['mongodb_id']}")
            print(f"   Total articles now: {result['total_articles']}\n")
        else:
            print(f"   ✗ Failed to add article: {result}\n")
            return False

        # Test 3: Try to add duplicate
        print("   Test 3: Duplicate detection")
        dup_result = db.add_article(test_article, save_immediately=True)

        if dup_result['status'] == 'duplicate':
            print(f"   ✓ Duplicate detected correctly\n")
        else:
            print(f"   ✗ Duplicate not detected: {dup_result}\n")
            return False

        # Test 4: Get all articles
        print("   Test 4: Retrieve articles")
        articles = db.get_all_articles()
        print(f"   ✓ Retrieved {len(articles)} articles\n")

        # Test 5: Check seen URLs
        print("   Test 5: Get seen URLs")
        seen_urls = db.get_seen_urls()
        print(f"   ✓ Found {len(seen_urls)} seen URLs\n")

        # Test 6: Check duplicates (URLs seen more than once)
        print("   Test 6: Get duplicate tracking")
        duplicates = db.get_duplicates()
        print(f"   ✓ Found {len(duplicates)} duplicate entries\n")

        # Test 7: Test scraper run tracking
        print("   Test 7: Test scraper run tracking")
        run_id = db.start_scraper_run(source="Test Source")
        print(f"   ✓ Started scraper run: {run_id}")

        db.update_scraper_run(run_id, articles=1, duplicates=1)
        print(f"   ✓ Updated scraper run statistics")

        db.end_scraper_run(run_id, status="completed")
        print(f"   ✓ Ended scraper run\n")

        # Test 8: Get scraper runs
        print("   Test 8: Get recent scraper runs")
        runs = db.get_scraper_runs(limit=5)
        print(f"   ✓ Retrieved {len(runs)} scraper runs\n")

        # Test 9: Create backup
        print("   Test 9: Create backup")
        backup_path = db.backup_database()
        print(f"   ✓ Backup created at: {backup_path}\n")

        # Final stats
        print("4. Final database statistics:")
        final_stats = db.get_database_stats()
        print(f"   Total articles: {final_stats['total_articles']}")
        print(f"   Total seen URLs: {final_stats['total_seen_urls']}")
        print(f"   Total duplicates: {final_stats['total_duplicates']}")
        print(f"   Total scraper runs: {final_stats['total_scraper_runs']}")
        print(f"   Database size: {final_stats['database_size_bytes']:,} bytes\n")

        print("="*80)
        print("✓ ALL TESTS PASSED!")
        print("="*80 + "\n")

        print("MongoDB is ready for migration!")
        print("\nNext steps:")
        print("1. Run migration: python migrate_to_mongodb.py")
        print("2. Start Flask app: DB_BACKEND=mongodb python app.py")
        print()

        return True

    except ImportError as e:
        print(f"\n✗ Import Error: {e}")
        print("\nMake sure pymongo is installed:")
        print("  pip install pymongo")
        return False

    except Exception as e:
        print(f"\n✗ MongoDB Connection Failed: {e}")
        print("\nPossible issues:")
        print("1. Wrong connection string in config/mongodb_config.json")
        print("2. MongoDB Atlas cluster not accessible")
        print("   - Check network access settings in Atlas")
        print("   - Verify IP whitelist includes your current IP")
        print("3. Invalid credentials")
        print("   - Check username and password in connection string")
        print("4. Database user not configured properly")
        print("   - Verify user has read/write permissions")
        print()

        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_mongodb_connection()
    sys.exit(0 if success else 1)
