# Local Development Guide

## 🚀 Quick Start for Local Development

### 1. Start MongoDB Locally
```bash
# Start MongoDB on port 27019 (custom configuration)
./start_mongodb.sh
```

### 2. Run the Local Development App
```bash
# Navigate to the unified app directory
cd unified_app

# Activate virtual environment
source venv/bin/activate

# Run the local development version
python app_local.py
```

The local app will:
- ✅ Connect to your local MongoDB on `localhost:27019`
- ✅ Create the database automatically
- ✅ Show development-friendly logs
- ✅ Include mock data so you can see the interface working
- ✅ Disable auto-scraping for faster development

### 3. Access the Application
- **Web UI:** http://localhost:5000
- **API:** http://localhost:5000/api/feed
- **Stats:** http://localhost:5000/api/stats

## 🔧 Troubleshooting

### MongoDB Connection Issues

If you see SSL connection errors like this:
```
SSL handshake failed: ac-li8nahr-shard-00-00.sez8ihw.mongodb.net:27017
```

**Solution:** Use the local development app (`app_local.py`) instead of the production app (`app.py`)

### MongoDB Not Running

If MongoDB is not running:
```bash
# Check if MongoDB is running
ps aux | grep mongod

# Start MongoDB
./start_mongodb.sh

# Or start it manually
mongod --port 27019 --dbpath ~/.mongodb_spine_scraper --logpath ~/.mongodb_spine_scraper/mongodb.log --fork
```

### Virtual Environment Issues

If you get import errors:
```bash
# Create and activate virtual environment
cd unified_app
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 📋 Development Features

### Mock Data
The local development app includes mock tweets and articles so you can see the interface working immediately:

- **Mock Articles:** 0 initially (will populate as you scrape)
- **Mock Tweets:** 2 sample tweets with spine-related content
- **Live Data:** Real spine articles when you trigger scraping

### Development Tools
- **Hot Reload:** Changes to templates and static files auto-refresh
- **Verbose Logging:** Full debug information in console
- **Error Handling:** Graceful fallbacks if database is unavailable
- **Mock Data:** Shows interface even without real data

### Available Endpoints
- `GET /` - Main feed interface
- `GET /api/feed` - JSON feed data with mock data
- `GET /api/stats` - System statistics
- `GET /api/sources` - Available content sources

## 🛠️ Development vs Production

| Feature | Development (`app_local.py`) | Production (`app.py`) |
|---------|------------------------------|----------------------|
| Database | Local MongoDB (27019) | MongoDB Atlas (Cloud) |
| Twitter | Mock data | Real Twitter API |
| Scraping | Disabled by default | Runs every 10 hours |
| Logging | Debug level | Info level |
| Auto-reload | Enabled | Disabled |
| Media files | Mock responses | Production handling |

## 📝 Testing Local Development

```bash
# Test database connection
python health_check.py

# Test the app locally
curl http://localhost:5000/api/stats

# Import some sample articles
cd unified_app
python -c "
from spine_market_scraper import SpineMarketScraper
scraper = SpineMarketScraper()
urls = scraper.scrape_article_listing_page('spine_market_group', limit=3)
for url in urls:
    article = scraper.scrape_article(url)
    print(f'Scraped: {article[\"title\"][:50]}...' if article else 'Failed to scrape')
"
```

## 🚫 Common Issues & Solutions

### 1. "ModuleNotFoundError"
```bash
# Solution: Activate virtual environment
source unified_app/venv/bin/activate
```

### 2. "MongoDB connection failed"
```bash
# Solution: Start MongoDB
./start_mongodb.sh
```

### 3. "No module named 'twitter'"
This is normal - Twitter scraping is optional for development.
The app will work with mock data.

### 4. Port already in use
```bash
# Find process using port 5000
lsof -i :5000

# Kill the process (replace PID with actual process ID)
kill -9 PID
```

## 🎯 Next Steps

Once local development is working:
1. **Test all features** in the local environment
2. **Push to GitHub** using the provided instructions
3. **Deploy to Render/Railway** using the deployment guide
4. **Configure MongoDB Atlas** for production environment

---

**Local Development:** ✅ Ready | **Production:** ✅ Ready | **Database:** 🗄️ Local MongoDB