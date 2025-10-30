#!/bin/bash
# Start MongoDB on custom port 27019 for spine market scraper

# Create data directory if it doesn't exist
MONGO_DATA_DIR="$HOME/.mongodb_spine_scraper"
mkdir -p "$MONGO_DATA_DIR"

echo "Starting MongoDB on port 27019..."
echo "Data directory: $MONGO_DATA_DIR"
echo "Database name: spine_articles_db"
echo ""

# Start MongoDB on custom port with custom data directory
mongod --port 27019 --dbpath "$MONGO_DATA_DIR" --logpath "$MONGO_DATA_DIR/mongodb.log" --fork

if [ $? -eq 0 ]; then
    echo "✓ MongoDB started successfully!"
    echo ""
    echo "To connect: mongosh --port 27019"
    echo "To stop: mongosh --port 27019 --eval 'db.adminCommand({shutdown: 1})'"
else
    echo "✗ Failed to start MongoDB"
    echo "Check logs: cat $MONGO_DATA_DIR/mongodb.log"
fi
