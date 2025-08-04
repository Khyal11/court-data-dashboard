#!/usr/bin/env python3
"""
Court Data Fetcher Application Runner

This script provides a convenient way to run the application with different configurations.
"""

import os
import sys
from app import app, db
from config import config

def create_app(config_name=None):
    """Create and configure the Flask application"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app.config.from_object(config[config_name])
    
    with app.app_context():
        db.create_all()
    
    return app

def init_db():
    """Initialize the database"""
    with app.app_context():
        db.create_all()
        print("Database initialized successfully!")

def run_tests():
    """Run the test suite"""
    import unittest
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'init-db':
            init_db()
            return
        elif command == 'test':
            success = run_tests()
            sys.exit(0 if success else 1)
        elif command == 'help':
            print("Available commands:")
            print("  init-db  - Initialize the database")
            print("  test     - Run the test suite")
            print("  help     - Show this help message")
            return
        else:
            print(f"Unknown command: {command}")
            print("Use 'python run.py help' for available commands")
            return
    
    # Default: run the application
    config_name = os.getenv('FLASK_ENV', 'development')
    app = create_app(config_name)
    
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = config_name == 'development'
    
    print(f"Starting Court Data Fetcher in {config_name} mode...")
    print(f"Server running on http://{host}:{port}")
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()