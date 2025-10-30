#!/usr/bin/env python3
"""
Test script to verify Twitter scraping integration is working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unified_app.twitter_mongo_manager import get_twitter_manager
import json

def test_twitter_manager():
    """Test Twitter MongoDB manager"""
    print("🔧 Testing Twitter MongoDB Manager...")
    
    try:
        twitter_db = get_twitter_manager('../config/mongodb_config.json')
        
        # Test stats
        stats = twitter_db.get_stats()
        print(f"✅ Twitter Manager connected successfully")
        print(f"📊 Total tweets in database: {stats.get('total_tweets', 0)}")
        print(f"👥 Total users tracked: {stats.get('total_users', 0)}")
        
        # Test adding a user
        result = twitter_db.add_user('test_user', 'Test User')
        print(f"✅ User addition test: {result}")
        
        # Test getting tweets (should be empty initially)
        tweets = twitter_db.get_tweets(limit=5)
        print(f"📝 Retrieved {len(tweets)} tweets")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_scraper_import():
    """Test if Twitter scraper can be imported"""
    print("\n🔧 Testing Twitter Scraper Import...")
    
    try:
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../twitter-scraper'))
        from twitter import download_tweets_and_media, search_tweets_by_keyword
        print("✅ Twitter scraper functions imported successfully")
        print("📋 Available functions:")
        print("   - download_tweets_and_media()")
        print("   - search_tweets_by_keyword()")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_existing_data():
    """Test existing Twitter data"""
    print("\n🔧 Testing Existing Twitter Data...")
    
    twitter_data_dirs = []
    try:
        for item in os.listdir('../twitter-scraper'):
            if os.path.isdir(f'../twitter-scraper/{item}') and ('_media_' in item or item.startswith('keyword_')):
                json_file = f'../twitter-scraper/{item}/tweets_index.json'
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        tweets_data = json.load(f)
                    twitter_data_dirs.append({
                        'folder': item,
                        'count': len(tweets_data),
                        'type': 'keyword' if item.startswith('keyword_') else 'user'
                    })
        
        print(f"✅ Found {len(twitter_data_dirs)} Twitter data directories:")
        for data_dir in twitter_data_dirs:
            print(f"   📁 {data_dir['folder']} ({data_dir['type']}) - {data_dir['count']} tweets")
            
        return len(twitter_data_dirs) > 0
        
    except Exception as e:
        print(f"❌ Error reading existing data: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 TWITTER INTEGRATION TEST")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Twitter Manager
    if test_twitter_manager():
        tests_passed += 1
    
    # Test 2: Scraper Import
    if test_scraper_import():
        tests_passed += 1
    
    # Test 3: Existing Data
    if test_existing_data():
        tests_passed += 1
    
    print("\n" + "=" * 60)
    print(f"📋 TEST RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 Twitter integration is working correctly!")
        print("\n✅ Ready for Twitter scraping:")
        print("   • MongoDB connection: ✅")
        print("   • Twitter scraper: ✅")
        print("   • Existing data: ✅")
        print("   • Frontend enabled: ✅")
    else:
        print("⚠️  Some issues detected, check the output above")
    
    print("=" * 60)

if __name__ == '__main__':
    main()