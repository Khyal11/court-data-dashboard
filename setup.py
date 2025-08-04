#!/usr/bin/env python3
"""
Setup script for Court Data Fetcher application
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def check_chrome():
    """Check if Chrome is installed"""
    chrome_paths = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print("✅ Google Chrome found")
            return True
    
    print("⚠️  Google Chrome not found. Please install Chrome for web scraping functionality.")
    return False

def create_env_file():
    """Create .env file from template"""
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("📝 Please edit .env file with your database credentials")
    else:
        print("❌ .env.example not found")

def install_dependencies():
    """Install Python dependencies"""
    try:
        print("📦 Installing Python dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def setup_database():
    """Initialize database"""
    try:
        print("🗄️  Setting up database...")
        from app import app, db
        with app.app_context():
            db.create_all()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("💡 Make sure PostgreSQL is running or use SQLite for development")

def main():
    """Main setup function"""
    print("🏛️  Court Data Fetcher Setup")
    print("=" * 40)
    
    # Check requirements
    check_python_version()
    check_chrome()
    
    # Setup steps
    create_env_file()
    install_dependencies()
    setup_database()
    
    print("\n🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your database credentials")
    print("2. Run: python app.py")
    print("3. Open http://localhost:5000 in your browser")
    print("\n📚 For more information, see README.md")

if __name__ == "__main__":
    main()