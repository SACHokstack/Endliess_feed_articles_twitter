#!/usr/bin/env python3
"""
Unified Flask App - Spine Articles + Twitter Scraper
Combines both scraping systems into a single interface with MongoDB Atlas backend
"""

import sys
import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import managers
from mongodb_manager import get_mongodb_manager
from unified_app.twitter_mongo_manager import get_twitter_manager

# Setup logging for production
DEBUG_MODE = os.getenv('DEBUG', 'False').lower() == 'true'

logging.basicConfig(
    level=logging.INFO if not DEBUG_MODE else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/unified_app.log') if not DEBUG_MODE else logging.StreamHandler(),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import scrapers first so we can handle import errors properly
from spine_market_scraper import SpineMarketScraper
try:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../twitter-scraper'))
    from twitter import download_tweets_and_media, search_tweets_by_keyword
    TWITTER_AVAILABLE = True
    logger.info("Twitter scraper functions imported successfully")
except ImportError as e:
    TWITTER_AVAILABLE = False
    logger.warning(f"Twitter scraper not available: {e}")
    # Twitter scraper functions not available

# Initialize Flask app
app = Flask(__name__)

# CORS configuration for production
CORS(app, origins=["*"] if DEBUG_MODE else [
    "https://*.onrender.com",
    "https://*.railway.app",
    "https://*.herokuapp.com"
])

# Initialize managers with environment-specific config
config_path = '../config/mongodb_config.json'
if os.getenv('MONGODB_CONNECTION_STRING'):
    # Use environment variables for production
    config_path = os.getenv('MONGODB_CONFIG_PATH', '../config/mongodb_config.json')
    if os.path.exists('config/mongodb_config.json'):
        config_path = 'config/mongodb_config.json'

spine_db = get_mongodb_manager(config_path)
twitter_db = get_twitter_manager(config_path)

# Background task tracking
scraping_tasks = {}
task_lock = threading.Lock()

# Scheduler for automatic scraping
scheduler = BackgroundScheduler()


def automatic_article_scraping():
    """
    Automatic scraping job that runs every 10 hours.
    Scrapes all spine article sources.
    Deduplication handled automatically via MongoDB seen_urls collection.
    """
    logger.info("Starting automatic article scraping...")

    try:
        scraper = SpineMarketScraper()
        sources = ['spine_market_group', 'ortho_spine_news', 'beckers_spine']
        limit = 20  # Scrape 20 articles per source

        for source_key in sources:
            logger.info(f"Auto-scraping from {source_key}...")

            # Get article URLs
            article_urls = scraper.scrape_article_listing_page(source_key, limit=limit)

            # Scrape each article - duplicates automatically handled by database
            for url in article_urls:
                article = scraper.scrape_article(url)
                if article:
                    # Add to database - deduplication happens automatically via seen_urls
                    spine_db.add_article(article)

        logger.info("Automatic scraping complete")

    except Exception as e:
        logger.error(f"Error in automatic scraping: {e}")


# Initialize scheduler
scheduler.add_job(
    func=automatic_article_scraping,
    trigger=IntervalTrigger(hours=10),
    id='auto_article_scraping',
    name='Automatic Article Scraping',
    replace_existing=True
)

# Run once on startup
def run_initial_scraping():
    """Run scraping once when app starts."""
    threading.Thread(target=automatic_article_scraping, daemon=True).start()

# Shutdown scheduler on exit
atexit.register(lambda: scheduler.shutdown())


def create_unified_feed_item(item: dict, item_type: str) -> dict:
    """
    Convert article or tweet to unified feed format.

    Args:
        item: Article or tweet dict
        item_type: 'article' or 'tweet'

    Returns:
        Unified format dict
    """
    if item_type == 'article':
        return {
            'id': item.get('url', ''),
            'type': 'article',
            'date': item.get('scraped_at', ''),
            'content': {
                'title': item.get('title', ''),
                'text': item.get('content', '')[:500] + '...' if len(item.get('content', '')) > 500 else item.get('content', ''),
                'summary': item.get('content', '')[:200] + '...' if len(item.get('content', '')) > 200 else item.get('content', '')
            },
            'source': {
                'name': item.get('website_name', 'Unknown'),
                'type': 'spine_article'
            },
            'media': [],
            'metadata': {
                'financial_mentions': item.get('financial_mentions', []),
                'spine_procedures': item.get('spine_procedures', []),
                'content_length': item.get('content_length', 0)
            },
            'url': item.get('url', '')
        }

    elif item_type == 'tweet':
        # Handle media files
        media = []
        if item.get('has_media') and item.get('media_files'):
            for media_file in item['media_files']:
                media.append({
                    'type': media_file.get('type', 'photo'),
                    'url': f"/media/{media_file.get('file', '')}",
                    'thumbnail': f"/media/{media_file.get('file', '')}"
                })

        return {
            'id': item.get('tweet_id', item.get('id', '')),
            'type': 'tweet',
            'date': item.get('date', ''),
            'content': {
                'title': f"Tweet by @{item.get('username', item.get('original_author', 'unknown'))}",
                'text': item.get('text', item.get('original_text', '')),
                'summary': item.get('text', item.get('original_text', ''))[:200]
            },
            'source': {
                'name': f"@{item.get('username', item.get('original_author', 'unknown'))}",
                'type': 'twitter'
            },
            'media': media,
            'metadata': {
                'tweet_type': item.get('type', 'ORIGINAL'),
                'has_media': item.get('has_media', False),
                'retweet_info': {
                    'is_retweet': item.get('type') == 'RETWEET',
                    'original_author': item.get('original_author'),
                    'retweet_author': item.get('retweet_author')
                } if item.get('type') == 'RETWEET' else None
            },
            'url': f"https://twitter.com/{item.get('original_author', item.get('username', 'unknown'))}/status/{item.get('tweet_id', item.get('id', ''))}"
        }


# Routes

@app.route('/')
def index():
    """Main page - unified feed interface."""
    return render_template('index.html')


@app.route('/article')
def article_detail():
    """Article detail page - shows full article content."""
    try:
        article_url = request.args.get('url')

        if not article_url:
            return render_template('404.html'), 404

        # URL decode the article URL
        from urllib.parse import unquote
        decoded_url = unquote(article_url)

        # Get article from database
        article = spine_db.get_article_by_id(decoded_url)

        if not article:
            logger.error(f"Article not found for URL: {decoded_url}")
            return render_template('404.html'), 404

        return render_template('article.html', article=article)

    except Exception as e:
        logger.error(f"Error getting article detail: {e}")
        return render_template('404.html'), 404


@app.route('/api/feed')
def get_unified_feed():
    """
    Get unified feed with articles and tweets sorted chronologically.

    Query params:
        limit: Max items per type (default 50)
        skip: Pagination offset (default 0)
        type: Filter by 'article', 'tweet', or 'both' (default 'both')
        source: Filter by specific source name
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        search: Search term
    """
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        skip = int(request.args.get('skip', 0))
        feed_type = request.args.get('type', 'both')
        source_filter = request.args.get('source')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search_term = request.args.get('search')

        unified_feed = []

        # Get articles and tweets, then randomize together for true mixing
        import random

        # Get articles
        if feed_type in ['both', 'article']:
            all_articles = spine_db.get_all_articles()
            
            # Apply filters to articles
            if source_filter:
                all_articles = [a for a in all_articles if a.get('website_name') == source_filter]
            if start_date:
                all_articles = [a for a in all_articles if a.get('scraped_at', '') >= start_date]
            if end_date:
                all_articles = [a for a in all_articles if a.get('scraped_at', '') <= end_date]
            if search_term:
                all_articles = [a for a in all_articles if search_term.lower() in a.get('content', '').lower() or search_term.lower() in a.get('title', '').lower()]

            # Convert to unified format
            for article in all_articles:
                unified_feed.append(create_unified_feed_item(article, 'article'))

        # Get tweets
        if feed_type in ['both', 'tweet']:
            # Get more tweets to account for filtering
            all_tweets = twitter_db.get_tweets(limit=1000, skip=0)
            
            # Apply filters to tweets
            if source_filter:
                all_tweets = [t for t in all_tweets if t.get('username') == source_filter or t.get('original_author') == source_filter]
            if start_date:
                all_tweets = [t for t in all_tweets if t.get('date', '') >= start_date]
            if end_date:
                all_tweets = [t for t in all_tweets if t.get('date', '') <= end_date]
            if search_term:
                all_tweets = [t for t in all_tweets if search_term.lower() in t.get('text', '').lower()]

            # Convert to unified format
            for tweet in all_tweets:
                unified_feed.append(create_unified_feed_item(tweet, 'tweet'))

        # Apply randomization to entire unified feed (articles + tweets together)
        # Use timestamp + object ID to ensure different order each refresh
        random.seed(datetime.now().microsecond + id(unified_feed))
        random.shuffle(unified_feed)
        logger.info(f"Shuffled {len(unified_feed)} items (articles + tweets mixed together)")

        # Apply pagination
        total_items = len(unified_feed)
        unified_feed = unified_feed[skip:skip+limit]

        return jsonify({
            'success': True,
            'feed': unified_feed,
            'total': total_items,
            'limit': limit,
            'skip': skip,
            'has_more': (skip + limit) < total_items
        })

    except Exception as e:
        logger.error(f"Error getting unified feed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """Get combined statistics from both systems."""
    try:
        spine_stats = spine_db.get_database_stats()
        twitter_stats = twitter_db.get_stats()

        combined_stats = {
            'spine_articles': {
                'total': spine_stats.get('total_articles', 0),
                'seen_urls': spine_stats.get('total_seen_urls', 0),
                'duplicates': spine_stats.get('total_duplicates', 0),
                'scraper_runs': spine_stats.get('total_scraper_runs', 0),
                'sources': spine_stats.get('sources', {})
            },
            'twitter': {
                'total_tweets': twitter_stats.get('total_tweets', 0),
                'total_users': twitter_stats.get('total_users', 0),
                'users': twitter_stats.get('users', {}),
                'keywords': twitter_stats.get('keywords', {})
            },
            'combined': {
                'total_items': spine_stats.get('total_articles', 0) + twitter_stats.get('total_tweets', 0),
                'last_updated': max(
                    spine_stats.get('last_updated', ''),
                    twitter_stats.get('last_updated', '')
                )
            }
        }

        return jsonify({
            'success': True,
            'stats': combined_stats
        })

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sources')
def get_sources():
    """Get all available sources (spine sources + Twitter users)."""
    try:
        scraper = SpineMarketScraper()
        spine_sources = [
            {
                'type': 'article',
                'key': key,
                'name': info['name'],
                'url': info['base_url']
            }
            for key, info in scraper.sources.items()
        ]

        twitter_users = twitter_db.get_users()
        twitter_sources = [
            {
                'type': 'tweet',
                'key': user['username'],
                'name': f"@{user['username']}",
                'display_name': user.get('display_name', user['username'])
            }
            for user in twitter_users
        ]

        return jsonify({
            'success': True,
            'sources': {
                'spine': spine_sources,
                'twitter': twitter_sources
            }
        })

    except Exception as e:
        logger.error(f"Error getting sources: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scraper/status')
def get_scraper_status():
    """
    Get status of automatic scraper.

    Returns:
        Status information about the automatic scraping job
    """
    try:
        job = scheduler.get_job('auto_article_scraping')

        if job:
            next_run = job.next_run_time.isoformat() if job.next_run_time else None

            return jsonify({
                'success': True,
                'status': {
                    'enabled': True,
                    'interval': '10 hours',
                    'next_run': next_run,
                    'sources': ['Spine Market Group', 'Ortho Spine News', "Becker's Spine Review"],
                    'articles_per_source': 20
                }
            })
        else:
            return jsonify({
                'success': True,
                'status': {
                    'enabled': False,
                    'message': 'Automatic scraping not configured'
                }
            })

    except Exception as e:
        logger.error(f"Error getting scraper status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scrape/twitter', methods=['POST'])
def scrape_twitter():
    """
    Trigger Twitter scraping.

    Body params:
        users: List of usernames
        keyword: Keyword to search (optional)
        limit: Tweets per user/keyword (default 50)
    """
    if not TWITTER_AVAILABLE:
        return jsonify({'success': False, 'error': 'Twitter scraper not available'}), 503

    try:
        data = request.get_json()
        users = data.get('users', [])
        keyword = data.get('keyword')
        limit = data.get('limit', 50)

        if not users and not keyword:
            return jsonify({'success': False, 'error': 'No users or keyword specified'}), 400

        task_id = f"twitter_{datetime.now().timestamp()}"

        def scrape_task():
            import asyncio
            import traceback
            import json
            import glob
            
            try:
                # Run Twitter scraping
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                if users:
                    # Scrape specific users
                    for username in users:
                        logger.info(f"Starting Twitter scrape for @{username}")
                        loop.run_until_complete(
                            download_tweets_and_media(
                                screen_name=username,
                                start_date='2025-10-01',
                                end_date='2025-10-27',
                                max_tweets=limit
                            )
                        )
                        
                        # Load tweets from downloaded files and add to MongoDB
                        user_folder_pattern = f'../twitter-scraper/{username}_media_*'
                        matching_folders = glob.glob(user_folder_pattern)
                        
                        if matching_folders:
                            latest_folder = matching_folders[-1]  # Get most recent
                            tweets_index_file = f'{latest_folder}/tweets_index.json'
                            
                            if os.path.exists(tweets_index_file):
                                with open(tweets_index_file, 'r', encoding='utf-8') as f:
                                    tweets_data = json.load(f)
                                
                                # Add each tweet to MongoDB
                                for tweet in tweets_data:
                                    # Ensure required fields for MongoDB manager
                                    tweet_for_db = {
                                        'tweet_id': tweet.get('id'),
                                        'username': username,
                                        'original_author': tweet.get('original_author', username),
                                        'text': tweet.get('text', ''),
                                        'date': tweet.get('date', ''),
                                        'type': tweet.get('type', 'ORIGINAL'),
                                        'has_media': tweet.get('has_media', False),
                                        'media_files': tweet.get('media_files', [])
                                    }
                                    
                                    twitter_db.add_tweet(tweet_for_db)
                        
                elif keyword:
                    # Search by keyword
                    logger.info(f"Starting Twitter search for '{keyword}'")
                    loop.run_until_complete(
                        search_tweets_by_keyword(
                            keyword=keyword,
                            start_date='2025-10-01',
                            end_date='2025-10-27',
                            product='Top',
                            max_tweets=limit
                        )
                    )
                    
                    # Load tweets from downloaded files and add to MongoDB
                    safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).strip()
                    safe_keyword = safe_keyword.replace(' ', '_')[:50]
                    
                    keyword_folder_pattern = f'../twitter-scraper/keyword_{safe_keyword}_*'
                    matching_folders = glob.glob(keyword_folder_pattern)
                    
                    if matching_folders:
                        latest_folder = matching_folders[-1]
                        tweets_index_file = f'{latest_folder}/tweets_index.json'
                        
                        if os.path.exists(tweets_index_file):
                            with open(tweets_index_file, 'r', encoding='utf-8') as f:
                                tweets_data = json.load(f)
                            
                            # Add each tweet to MongoDB
                            for tweet in tweets_data:
                                tweet_for_db = {
                                    'tweet_id': tweet.get('id'),
                                    'username': tweet.get('original_author', 'unknown'),
                                    'original_author': tweet.get('original_author', 'unknown'),
                                    'text': tweet.get('text', ''),
                                    'date': tweet.get('date', ''),
                                    'type': tweet.get('type', 'ORIGINAL'),
                                    'has_media': tweet.get('has_media', False),
                                    'media_files': tweet.get('media_files', []),
                                    'keyword': keyword
                                }
                                
                                twitter_db.add_tweet(tweet_for_db)
                    
                loop.close()
                
                with task_lock:
                    scraping_tasks[task_id]['status'] = 'completed'
                    
            except Exception as e:
                logger.error(f"Twitter scraping error: {e}")
                logger.error(traceback.format_exc())
                with task_lock:
                    scraping_tasks[task_id]['status'] = 'failed'
                    scraping_tasks[task_id]['error'] = str(e)

        with task_lock:
            scraping_tasks[task_id] = {
                'status': 'running',
                'type': 'twitter',
                'users': users,
                'keyword': keyword,
                'started_at': datetime.now().isoformat()
            }

        thread = threading.Thread(target=scrape_task)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Twitter scraping started'
        })

    except Exception as e:
        logger.error(f"Error starting Twitter scraping: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/<task_id>')
def get_task_status(task_id):
    """Get status of a scraping task."""
    with task_lock:
        if task_id not in scraping_tasks:
            return jsonify({'success': False, 'error': 'Task not found'}), 404

        return jsonify({
            'success': True,
            'task': scraping_tasks[task_id]
        })


@app.route('/api/twitter/users', methods=['POST'])
def add_twitter_user():
    """Add a Twitter user to track."""
    try:
        data = request.get_json()
        username = data.get('username')
        display_name = data.get('display_name')

        if not username:
            return jsonify({'success': False, 'error': 'Username required'}), 400

        result = twitter_db.add_user(username, display_name)
        return jsonify({'success': True, 'result': result})

    except Exception as e:
        logger.error(f"Error adding Twitter user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/twitter/users/<username>', methods=['DELETE'])
def remove_twitter_user(username):
    """Remove a Twitter user from tracking."""
    try:
        result = twitter_db.remove_user(username)
        return jsonify({'success': True, 'result': result})

    except Exception as e:
        logger.error(f"Error removing Twitter user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/media/<path:filename>')
def serve_twitter_media(filename):
    """Serve Twitter media files from various directories"""
    try:
        # Search for the media file in all Twitter scraping directories
        import glob
        
        # Get the base directory for twitter scraper
        twitter_scraper_base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'twitter-scraper')
        
        # Search for the file in all media_tweets directories
        pattern = f'{twitter_scraper_base}/*/media_tweets/{filename}'
        matching_files = glob.glob(pattern)
        
        if matching_files:
            media_path = matching_files[0]
            logger.info(f"Serving media file: {media_path}")
            
            # Get the directory and filename
            media_dir = os.path.dirname(media_path)
            
            from flask import send_from_directory
            return send_from_directory(media_dir, filename)
        else:
            logger.warning(f"Media file not found: {filename}")
            # Return 404 for missing files
            return jsonify({'error': 'Media file not found', 'filename': filename}), 404
            
    except Exception as e:
        logger.error(f"Error serving media file {filename}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/media/keyword/<keyword>/<path:filename>')
def serve_keyword_media(keyword, filename):
    """Serve Twitter media files from keyword searches"""
    try:
        # Get the base directory for twitter scraper
        twitter_scraper_base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'twitter-scraper')
        
        # Search for the file in keyword directories
        pattern = f'{twitter_scraper_base}/keyword_{keyword}*/media_tweets/{filename}'
        matching_files = glob.glob(pattern)
        
        if matching_files:
            media_path = matching_files[0]
            logger.info(f"Serving keyword media file: {media_path}")
            
            # Get the directory and filename
            media_dir = os.path.dirname(media_path)
            
            from flask import send_from_directory
            return send_from_directory(media_dir, filename)
        else:
            logger.warning(f"Keyword media file not found: {filename}")
            # Return 404 for missing files
            return jsonify({'error': 'Media file not found', 'keyword': keyword, 'filename': filename}), 404
            
    except Exception as e:
        logger.error(f"Error serving keyword media file {filename}: {e}")
        return jsonify({'error': str(e)}), 500


# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    
    logger.info("Starting Unified Flask App")
    logger.info(f"Debug Mode: {DEBUG_MODE}")
    logger.info(f"Port: {port}")
    logger.info(f"Spine DB: {spine_db.config['database_name']}")

    # Start scheduler
    scheduler.start()
    logger.info("Automatic article scraping scheduler started (every 10 hours)")

    # Run initial scraping in background (only in non-production for performance)
    if not DEBUG_MODE:
        logger.info("Starting initial article scraping...")
        run_initial_scraping()

    # Production vs development server configuration
    if DEBUG_MODE:
        # Development server with auto-reload
        app.run(debug=True, host='0.0.0.0', port=port, use_reloader=True)
    else:
        # Production server (should use Gunicorn instead)
        logger.warning("Using Flask development server in production. Consider using Gunicorn.")
        app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
