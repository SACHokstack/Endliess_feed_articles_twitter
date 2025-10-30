#!/usr/bin/env python3
"""
Test script to verify deduplication works properly in MongoDB.
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongodb_manager import get_mongodb_manager

def test_deduplication():
    """Test that duplicate detection works correctly."""
    print("=" * 60)
    print("DEDUPLICATION TEST")
    print("=" * 60)

    # Get MongoDB manager
    db = get_mongodb_manager('../config/mongodb_config.json')

    # Create a test article
    test_article = {
        'url': 'https://test-deduplication-article-12345.com/article',
        'title': 'Test Article for Deduplication',
        'content': 'This is a test article to verify deduplication works.',
        'website_name': 'Test Source',
        'content_length': 100
    }

    print("\n1. Testing first insertion (should succeed)...")
    result1 = db.add_article(test_article.copy())
    print(f"   Result: {result1['status']}")

    if result1['status'] == 'success':
        print("   ✓ First insertion successful")
    else:
        print("   ✗ First insertion failed")
        return False

    print("\n2. Testing duplicate insertion (should be detected)...")
    result2 = db.add_article(test_article.copy())
    print(f"   Result: {result2['status']}")

    if result2['status'] == 'duplicate':
        print("   ✓ Duplicate detected correctly!")
    else:
        print("   ✗ Duplicate NOT detected - this is a problem!")
        return False

    print("\n3. Verifying URL is in seen_urls collection...")
    is_dup = db.is_duplicate(test_article['url'])
    if is_dup:
        print("   ✓ URL found in seen_urls collection")
    else:
        print("   ✗ URL NOT found in seen_urls - this is a problem!")
        return False

    print("\n4. Checking stats...")
    stats = db.get_database_stats()
    print(f"   Total articles: {stats['total_articles']}")
    print(f"   Total duplicates: {stats['total_duplicates']}")

    print("\n" + "=" * 60)
    print("DEDUPLICATION TEST PASSED ✓")
    print("=" * 60)

    return True

if __name__ == '__main__':
    try:
        success = test_deduplication()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
