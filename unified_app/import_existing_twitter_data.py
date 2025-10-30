#!/usr/bin/env python3
"""
Import existing Twitter data into MongoDB for unified feed display
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unified_app.twitter_mongo_manager import get_twitter_manager

def import_twitter_data_to_mongodb():
    """Import all existing Twitter data into MongoDB"""
    print("=" * 60)
    print("📥 IMPORTING TWITTER DATA TO MONGODB")
    print("=" * 60)
    
    try:
        twitter_db = get_twitter_manager('../config/mongodb_config.json')
        
        # Find all Twitter data directories
        twitter_data_dirs = []
        twitter_scraper_dir = '../twitter-scraper'
        
        if os.path.exists(twitter_scraper_dir):
            for item in os.listdir(twitter_scraper_dir):
                if os.path.isdir(os.path.join(twitter_scraper_dir, item)) and ('_media_' in item or item.startswith('keyword_')):
                    json_file = os.path.join(twitter_scraper_dir, item, 'tweets_index.json')
                    if os.path.exists(json_file):
                        twitter_data_dirs.append({
                            'folder': item,
                            'json_path': json_file,
                            'type': 'keyword' if item.startswith('keyword_') else 'user'
                        })
        
        print(f"🔍 Found {len(twitter_data_dirs)} Twitter data directories")
        total_imported = 0
        total_duplicates = 0
        
        for data_dir in twitter_data_dirs:
            print(f"\n📁 Processing: {data_dir['folder']}")
            
            # Load tweets from JSON
            with open(data_dir['json_path'], 'r', encoding='utf-8') as f:
                tweets_data = json.load(f)
            
            print(f"   📊 Found {len(tweets_data)} tweets")
            
            # Import each tweet to MongoDB
            imported_count = 0
            duplicates_count = 0
            
            for tweet in tweets_data:
                try:
                    # Prepare tweet for MongoDB
                    tweet_for_db = {
                        'tweet_id': tweet.get('id'),
                        'username': tweet.get('original_author', tweet.get('username', 'unknown')),
                        'original_author': tweet.get('original_author', tweet.get('username', 'unknown')),
                        'text': tweet.get('text', ''),
                        'date': tweet.get('date', ''),
                        'type': tweet.get('type', 'ORIGINAL'),
                        'has_media': tweet.get('has_media', False),
                        'media_files': tweet.get('media_files', [])
                    }
                    
                    # Add keyword for keyword searches
                    if data_dir['type'] == 'keyword':
                        # Extract keyword from folder name
                        if 'keyword_' in data_dir['folder']:
                            keyword = data_dir['folder'].split('keyword_')[1].split('_20')[0]
                            tweet_for_db['keyword'] = keyword
                    
                    # Add to MongoDB
                    result = twitter_db.add_tweet(tweet_for_db)
                    
                    if result['status'] == 'success':
                        imported_count += 1
                    elif result['status'] == 'duplicate':
                        duplicates_count += 1
                        
                except Exception as e:
                    print(f"   ❌ Error importing tweet {tweet.get('id', 'unknown')}: {e}")
            
            print(f"   ✅ Imported: {imported_count}")
            print(f"   🔄 Duplicates: {duplicates_count}")
            
            total_imported += imported_count
            total_duplicates += duplicates_count
            
            # Add user to tracked users for user folders
            if data_dir['type'] == 'user':
                username = data_dir['folder'].split('_media_')[0]
                user_result = twitter_db.add_user(username, username)
                print(f"   👤 User tracked: @{username} ({user_result.get('status', 'unknown')})")
        
        print(f"\n{'=' * 60}")
        print(f"📊 IMPORT SUMMARY")
        print(f"{'=' * 60}")
        print(f"✅ Successfully imported: {total_imported} tweets")
        print(f"🔄 Duplicates skipped: {total_duplicates} tweets")
        print(f"📁 Data directories processed: {len(twitter_data_dirs)}")
        
        # Get final stats
        stats = twitter_db.get_stats()
        print(f"\n📈 Final Database Stats:")
        print(f"   📊 Total tweets in MongoDB: {stats.get('total_tweets', 0)}")
        print(f"   👥 Total users tracked: {stats.get('total_users', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
        return False

def main():
    """Main function"""
    success = import_twitter_data_to_mongodb()
    
    if success:
        print(f"\n🎉 Twitter data import completed successfully!")
        print(f"\n✨ You can now:")
        print(f"   1. Open the unified app: http://localhost:5000")
        print(f"   2. See Twitter tweets in the unified feed")
        print(f"   3. Filter by 'Tweets Only' to see just Twitter content")
        print(f"   4. Click on tweet links to view on Twitter")
        print(f"   5. Add more users via the Twitter scraping interface")
    else:
        print(f"\n❌ Import failed. Check the error messages above.")
    
    print("=" * 60)

if __name__ == '__main__':
    main()