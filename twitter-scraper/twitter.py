"""
Mock Twitter module for production deployment
Provides placeholder functions when Twitter scraping is not available
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def download_tweets_and_media(screen_name: str, start_date: str = None, end_date: str = None, max_tweets: int = 50):
    """
    Mock function for downloading tweets and media
    Returns empty list in production environment
    """
    logger.warning(f"Twitter scraping not available in production for user: {screen_name}")
    logger.info("This would normally download tweets using Twikit library")
    return []


async def search_tweets_by_keyword(keyword: str, start_date: str = None, end_date: str = None, 
                                 product: str = "Top", max_tweets: int = 50):
    """
    Mock function for searching tweets by keyword
    Returns empty list in production environment
    """
    logger.warning(f"Twitter search not available in production for keyword: {keyword}")
    logger.info("This would normally search tweets using Twikit library")
    return []


def get_twitter_client():
    """
    Mock function to get Twitter client
    Returns None in production
    """
    logger.warning("Twitter client not available in production environment")
    return None


def scrape_twitter_data(*args, **kwargs):
    """
    Mock function for general Twitter scraping
    Returns empty data structure
    """
    logger.warning("Twitter data scraping not available in production")
    return {"tweets": [], "media": [], "users": []}