# Local Media Upload Instructions

## Running the Upload Script on Your Laptop

Since you want to run the media upload separately from your laptop, follow these steps:

### Step 1: Copy Files to Your Laptop
You'll need these files on your local laptop:
1. `upload_media_to_gridfs.py` - The upload script
2. `unified_app/twitter_mongo_manager.py` - The Twitter manager (for GridFS integration)
3. `config/mongodb_config.json` - Your MongoDB configuration

### Step 2: Set Up Dependencies
Install required packages on your laptop:
```bash
pip install pymongo
```
**Note**: `gridfs` is included with `pymongo`, so you don't need to install it separately.

### Step 3: Configure MongoDB Connection
Update your `mongodb_config.json` file with your MongoDB Atlas connection string:
```json
{
  "connection_string": "mongodb+srv://sachivcsv_db_user:tfLNVtw5PlMOFxI7@cluster0.sez8ihw.mongodb.net/spine_scraper",
  "database_name": "Beautiful_Spine"
}
```

### Step 4: Run the Script
From your laptop's command line:

**Test run (recommended first):**
```bash
python upload_media_to_gridfs.py --dry-run
```

**Actual upload:**
```bash
python upload_media_to_gridfs.py
```

### What It Will Do:
1. Scan all your local `twitter-scraper/*/media_tweets/` directories
2. Upload each media file to MongoDB GridFS
3. Update your tweet records with GridFS file IDs
4. Provide detailed progress reporting

### Expected Output:
```
🚀 Starting media upload to MongoDB GridFS
==================================================
🔍 Scanning for media files in: twitter-scraper
  📁 Scanning: twitter-scraper/BasselDiebo_media_20250513_to_20251027/media_tweets
  📁 Scanning: twitter-scraper/keyword_spine_20251001_to_20251027/media_tweets
📊 Found 45 media files

📋 Upload Summary:
   Files to process: 45
   Total size: 156,789,234 bytes
   Estimated upload time: 90.0 seconds
```

### After Upload:
- All your media files will be stored in MongoDB GridFS
- Your web app will automatically serve them from the cloud
- You can delete local media files to save space
- Your application will work on any cloud platform (Render, Railway, etc.)

### Files Structure:
```
Your Laptop:
twitter-scraper/
├── BasselDiebo_media_20250513_to_20251027/
│   ├── text_tweets/
│   └── media_tweets/          ← Upload these files to GridFS
├── keyword_spine_20251001_to_20251027/
│   ├── text_tweets/
│   └── media_tweets/          ← Upload these files to GridFS
└── ... (other folders)

MongoDB Atlas:
database: Beautiful_Spine
├── GridFS (media files stored here)
├── tweets (updated with GridFS references)
└── other collections...