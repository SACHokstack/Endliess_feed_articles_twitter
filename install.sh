#!/bin/bash

# Endliess Feed Articles Twitter - Quick Setup Script
# This script automates the installation and setup process

set -e

echo "🏥 Endliess Feed Articles Twitter - Quick Setup"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3 is installed
print_status "Checking Python 3 installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.7+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_success "Python $PYTHON_VERSION found"

# Check if pip is installed
print_status "Checking pip installation..."
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install pip first."
    exit 1
fi
print_success "pip found"

# Create virtual environment
print_status "Creating virtual environment..."
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists. Removing..."
    rm -rf venv
fi

python3 -m venv venv
print_success "Virtual environment created"

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip
print_success "pip upgraded"

# Install requirements
print_status "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_success "Dependencies installed from requirements.txt"
else
    print_warning "requirements.txt not found. Installing basic dependencies..."
    pip install Flask pymongo requests beautifulsoup4 Flask-CORS APScheduler
    print_success "Basic dependencies installed"
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs
mkdir -p unified_app/logs
print_success "Directories created"

# Check MongoDB connection
print_status "Checking MongoDB configuration..."
if [ -f "config/mongodb_config.json" ]; then
    print_success "MongoDB config found"
    
    # Test local MongoDB if available
    if command -v mongosh &> /dev/null; then
        print_status "Testing local MongoDB connection..."
        if mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
            print_success "Local MongoDB is running"
        else
            print_warning "Local MongoDB is not running. You can start it with: ./start_mongodb.sh"
        fi
    else
        print_warning "MongoDB client not found. Make sure MongoDB Atlas is configured"
    fi
else
    print_warning "MongoDB config not found. Please configure config/mongodb_config.json"
fi

# Check environment variables
print_status "Checking environment variables..."
if [ -f ".env" ]; then
    print_success ".env file found"
else
    print_warning ".env file not found. Copying from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_warning "Please edit .env file with your actual configuration values"
    else
        print_warning ".env.example not found. Please create .env manually"
    fi
fi

# Run health check if available
print_status "Running health check..."
if [ -f "health_check.py" ]; then
    if python3 health_check.py; then
        print_success "Health check passed"
    else
        print_warning "Health check failed. Please review the output above"
    fi
else
    print_warning "health_check.py not found. Skipping health check"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your MongoDB Atlas credentials"
echo "2. Start the application:"
echo "   cd unified_app && python app.py"
echo ""
echo "Or for production:"
echo "   export DEBUG=False"
echo "   export MONGODB_CONNECTION_STRING=your_connection_string"
echo "   cd unified_app && python app.py"
echo ""
echo "Access the application at: http://localhost:5000"
echo ""
echo "For deployment to Render/Railway, see DEPLOYMENT_GUIDE.md"
echo ""