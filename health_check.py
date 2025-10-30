#!/usr/bin/env python3
"""
Production Health Check Script
Verify deployment readiness and test key functionality
"""

import os
import sys
import json
import requests
from datetime import datetime

def check_environment():
    """Check environment variables and configuration"""
    print("🔍 Checking environment configuration...")
    
    required_vars = ['DEBUG', 'MONGODB_CONNECTION_STRING', 'MONGODB_DATABASE_NAME']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    print(f"✅ Environment variables OK (DEBUG={debug_mode})")
    return True

def check_mongodb_connection():
    """Test MongoDB connection"""
    print("🔗 Testing MongoDB connection...")
    
    try:
        from pymongo import MongoClient
        
        conn_string = os.getenv('MONGODB_CONNECTION_STRING')
        db_name = os.getenv('MONGODB_DATABASE_NAME', 'Beautiful_Spine')
        
        client = MongoClient(conn_string, serverSelectionTimeoutMS=5000)
        client.server_info()
        
        # Test database access
        db = client[db_name]
        stats = db.command('dbStats')
        
        print(f"✅ MongoDB connection OK (Database: {db_name})")
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False

def check_app_import():
    """Test Flask app import"""
    print("🐍 Testing Flask app import...")
    
    try:
        sys.path.append('unified_app')
        from app import app
        
        print("✅ Flask app import OK")
        return True
        
    except Exception as e:
        print(f"❌ Flask app import failed: {e}")
        return False

def check_static_files():
    """Check if static files exist"""
    print("📁 Checking static files...")
    
    static_files = [
        'unified_app/static/css/main.css',
        'unified_app/static/js/app.js',
        'unified_app/templates/index.html'
    ]
    
    missing_files = []
    for file_path in static_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing static files: {', '.join(missing_files)}")
        return False
    
    print("✅ Static files OK")
    return True

def check_production_files():
    """Check production configuration files"""
    print("📋 Checking production configuration files...")
    
    required_files = [
        'Procfile',
        'runtime.txt',
        'requirements.txt'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing production files: {', '.join(missing_files)}")
        return False
    
    print("✅ Production configuration files OK")
    return True

def check_local_server():
    """Test local server startup (if not in production)"""
    if os.getenv('DEBUG', 'False').lower() != 'true':
        print("🚀 Skipping local server test (not in DEBUG mode)")
        return True
    
    print("🚀 Testing local server startup...")
    
    try:
        from unified_app.app import app
        
        with app.test_client() as client:
            response = client.get('/')
            if response.status_code == 200:
                print("✅ Local server test OK")
                return True
            else:
                print(f"❌ Local server returned status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Local server test failed: {e}")
        return False

def main():
    """Run all health checks"""
    print("🏥 Production Health Check")
    print("=" * 50)
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    print()
    
    checks = [
        check_environment,
        check_mongodb_connection,
        check_app_import,
        check_static_files,
        check_production_files,
        check_local_server
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ {check.__name__} failed: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("📊 Health Check Summary")
    print("=" * 50)
    print(f"Checks Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All checks passed! Ready for deployment.")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix issues before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())