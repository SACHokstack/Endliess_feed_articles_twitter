# Unified Spine News & Twitter Feed

A Flask-based web application that combines spine industry articles and Twitter feeds into a single unified interface with MongoDB Atlas backend.

## Features

- **Unified Chronological Feed**: View both articles and tweets in a single, sorted timeline
- **Multiple Data Sources**:
  - Spine Market Group
  - Ortho Spine News
  - Becker's Spine Review
  - Twitter users and keywords
- **MongoDB Atlas Backend**: Cloud-based data storage for both articles and tweets
- **Advanced Filtering**: Filter by content type, date range, source, and keywords
- **Dark/Light Theme**: Toggle between dark and light color schemes
- **Real-time Scraping**: Background scraping with progress tracking
- **Media Support**: Display images and videos from tweets with lightbox viewer

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure MongoDB Atlas:
   - Update `../config/mongodb_config.json` with your Atlas connection string
   - Database name should be `Beautiful_Spine`

3. Run the application:
```bash
python app.py
```

4. Open browser to `http://localhost:5000`

## Project Structure

```
unified_app/
├── app.py                          # Main Flask application
├── twitter_mongo_manager.py        # Twitter MongoDB integration
├── templates/
│   └── index.html                  # Main page template
├── static/
│   ├── css/
│   │   ├── main.css               # Base styles and layout
│   │   ├── theme.css              # Dark/light theme variables
│   │   └── cards.css              # Feed card components
│   └── js/
│       ├── app.js                 # Main application logic
│       ├── feed.js                # Feed management
│       └── theme.js               # Theme switcher
└── logs/
    └── unified_app.log            # Application logs
```

## Usage

### Scraping Spine Articles

1. Select sources from the left sidebar
2. Set articles per source (1-50)
3. Click "Scrape Articles"
4. Monitor progress bar
5. New articles appear in feed automatically

### Scraping Twitter

1. Add Twitter users by username (without @)
2. Or enter a keyword to search
3. Set tweet limit (1-200)
4. Click "Scrape Tweets"
5. Tweets appear in unified feed

### Filtering

Right sidebar offers multiple filter options:
- **Content Type**: All, Articles Only, or Tweets Only
- **Date Range**: Filter by start and end dates
- **Search**: Full-text search across content
- **Source**: Filter by specific source or user

### Theme Toggle

Click the moon/sun icon in top-right to switch between dark and light themes. Preference is saved in browser.

## API Endpoints

- `GET /` - Main page
- `GET /api/feed` - Get unified feed (supports filters)
- `GET /api/stats` - Get combined statistics
- `GET /api/sources` - Get all available sources
- `POST /api/scrape/spine` - Start spine article scraping
- `POST /api/scrape/twitter` - Start Twitter scraping
- `GET /api/tasks/<task_id>` - Monitor scraping task
- `POST /api/twitter/users` - Add Twitter user
- `DELETE /api/twitter/users/<username>` - Remove Twitter user

## MongoDB Collections

The app uses MongoDB Atlas with the following collections:

- **articles**: Spine articles with metadata
- **seen_urls**: URL tracking for duplicate detection
- **scraper_runs**: Scraping session logs
- **stats**: Article statistics
- **tweets**: Twitter data with media references
- **twitter_users**: Tracked Twitter users
- **twitter_stats**: Twitter statistics

## Requirements

- Python 3.8+
- MongoDB Atlas account
- Flask 3.0+
- Modern web browser (Chrome, Firefox, Safari, Edge)

## Notes

- Twitter scraping requires Twitter API credentials (configured in parent twitter-scraper directory)
- Spine article scraping uses BeautifulSoup (no API key required)
- All data is stored in MongoDB Atlas cloud database
- Media files from tweets are stored locally with paths in database

## License

MIT License
