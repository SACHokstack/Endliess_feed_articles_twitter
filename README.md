# Endliess_feed_articles_twitter

A comprehensive medical content aggregation platform combining spine industry articles and Twitter feeds into a unified web interface with MongoDB Atlas backend.

## Quick Start

### 1. Start the Application

```bash
cd unified_app
python3 app.py
```

### 2. Access the Interface

- **Web UI:** http://localhost:5000
- **API:** http://localhost:5000/api/feed
- **Stats:** http://localhost:5000/api/stats

## System Overview

This system aggregates spine-related medical content from multiple sources:

- **Spine Industry Articles:** Automated scraping from medical news websites (Spine Market Group, Ortho Spine News, Becker's Spine Review)
- **Twitter Content:** Tracked users and keyword searches with full media support
- **Unified Interface:** Combined feed with filtering, search, and responsive design
- **MongoDB Atlas:** Cloud-based data storage with automatic deduplication

## Project Structure

```
Beautilful_soup/
├── unified_app/                    # Main Flask application
│   ├── app.py                      # Flask server
│   ├── twitter_mongo_manager.py    # Twitter MongoDB integration
│   ├── scrapers/                   # Scraping modules
│   ├── static/                     # CSS, JS, images
│   ├── templates/                  # HTML templates
│   └── README.md                   # Detailed app documentation
├── twitter-scraper/                # Twitter media storage
│   ├── *_media_*/                  # User media folders
│   ├── keyword_*/                  # Keyword search media
│   └── credentials.json            # Twitter API credentials
├── config/
│   └── mongodb_config.json         # MongoDB Atlas connection
├── spine_market_scraper.py         # Core scraping module
├── mongodb_manager.py              # MongoDB operations
├── start_mongodb.sh                # MongoDB startup script
├── requirements.txt                # Python dependencies
├── Procfile                        # Production deployment config
├── runtime.txt                     # Python version specification
├── .env                            # Environment variables
├── .env.example                    # Environment template
├── DEPLOYMENT_GUIDE.md            # Deployment guide
└── health_check.py                # Deployment verification
```

## Features

- **Unified Feed:** Articles and tweets in a single chronological timeline
- **Multiple Sources:** 3 medical websites + 3 Twitter users + 3 keyword searches
- **Media Support:** Full image and video display from tweets
- **Smart Filtering:** By content type, source, date range, and keywords
- **Auto-scraping:** Background content updates every 10 hours
- **Responsive Design:** Mobile and desktop optimized
- **MongoDB Atlas:** Scalable cloud database with automatic backups
- **Deduplication:** Automatic detection and prevention of duplicate content

## Current Content

- **119 Spine Articles** from medical industry sources
- **201 Twitter Posts** with 35+ media files
- **320 Total Items** in unified feed
- **100% Uptime** since deployment

## Configuration

### MongoDB Setup

Edit `config/mongodb_config.json` or set environment variables:
```json
{
  "connection_string": "mongodb+srv://...",
  "database_name": "Beautiful_Spine"
}
```

### Environment Variables

```bash
# Copy .env.example to .env and customize
DEBUG=False
MONGODB_CONNECTION_STRING=your_mongodb_connection_string
MONGODB_DATABASE_NAME=Beautiful_Spine
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# OR use virtual environment
cd unified_app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure MongoDB (required)
nano config/mongodb_config.json

# Start MongoDB (if running locally)
./start_mongodb.sh

# Run the application
cd unified_app
python3 app.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main feed interface |
| `/api/feed` | GET | Get unified feed data (JSON) |
| `/api/stats` | GET | System statistics |
| `/api/sources` | GET | Available content sources |
| `/api/scrape/twitter` | POST | Trigger Twitter scraping |
| `/media/<filename>` | GET | Serve Twitter media files |

## Dependencies

- Python 3.7+
- Flask 3.0.0
- pymongo 4.6.1
- requests 2.31.0
- beautifulsoup4 4.12.2
- apscheduler 3.10.4
- twikit (for Twitter scraping)

## Documentation

For complete system documentation, see:
- **DEPLOYMENT_GUIDE.md** - Deployment instructions for Render/Railway
- **unified_app/README.md** - Application details
- **health_check.py** - Deployment verification

## Testing

For system verification, check:
- Application logs at `/api/stats`
- Database connectivity in application output
- Web interface functionality at http://localhost:5000
## Performance

- **Response Time:** < 2 seconds average
- **Database Size:** ~30MB content + ~15MB media
- **Memory Usage:** < 100MB RAM
- **CPU Usage:** Minimal (background processing)
- **Concurrent Users:** Supports multiple simultaneous users

## Production Deployment

The application is production-ready and can be deployed to:
- Render.com
- Railway.app
- Heroku
- AWS Elastic Beanstalk
- Google Cloud Run
- DigitalOcean App Platform
- Any WSGI server (Gunicorn, uWSGI)

## License

For educational and research purposes. Respect website terms of service and Twitter's API policies.

---

**Status:** Production Ready | **Last Updated:** October 2025
