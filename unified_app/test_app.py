#!/usr/bin/env python3
"""
Test script for unified app
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing unified app...")
print("=" * 60)

# Test 1: Import managers
print("\n1. Testing imports...")
try:
    from mongodb_manager import get_mongodb_manager
    print("   ✓ mongodb_manager imported")
except Exception as e:
    print(f"   ✗ Failed to import mongodb_manager: {e}")
    sys.exit(1)

try:
    from twitter_mongo_manager import get_twitter_manager
    print("   ✓ twitter_mongo_manager imported")
except Exception as e:
    print(f"   ✗ Failed to import twitter_mongo_manager: {e}")
    sys.exit(1)

# Test 2: Connect to databases
print("\n2. Testing database connections...")
try:
    spine_db = get_mongodb_manager('../config/mongodb_config.json')
    print(f"   ✓ Spine DB connected: {spine_db.config['database_name']}")
except Exception as e:
    print(f"   ✗ Failed to connect to spine DB: {e}")
    sys.exit(1)

try:
    twitter_db = get_twitter_manager('../config/mongodb_config.json')
    print(f"   ✓ Twitter DB connected: {twitter_db.config['database_name']}")
except Exception as e:
    print(f"   ✗ Failed to connect to twitter DB: {e}")
    sys.exit(1)

# Test 3: Get stats
print("\n3. Testing database operations...")
try:
    spine_stats = spine_db.get_database_stats()
    print(f"   ✓ Spine articles: {spine_stats.get('total_articles', 0)}")
    print(f"   ✓ Seen URLs: {spine_stats.get('total_seen_urls', 0)}")
except Exception as e:
    print(f"   ✗ Failed to get spine stats: {e}")

try:
    twitter_stats = twitter_db.get_stats()
    print(f"   ✓ Tweets: {twitter_stats.get('total_tweets', 0)}")
    print(f"   ✓ Twitter users: {twitter_stats.get('total_users', 0)}")
except Exception as e:
    print(f"   ✗ Failed to get twitter stats: {e}")

# Test 4: Import Flask app
print("\n4. Testing Flask app import...")
try:
    from app import app
    print("   ✓ Flask app imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import Flask app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print("\nUnified app is ready to run!")
print("Start the app with: python app.py")
