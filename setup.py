#!/usr/bin/env python3
"""
Market Signal MVP Setup Script
Automates the initial setup and data population
"""

import os
import sys
import subprocess
import sqlite3
from datetime import datetime

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies. Please run: pip install -r requirements.txt")
        return False
    return True

def setup_database():
    """Initialize the SQLite database"""
    print("🗄️  Setting up database...")
    
    from data_fetcher import StockDataFetcher
    from sentiment_analyzer import NewsSentimentAnalyzer
    
    try:
        # Initialize database tables
        fetcher = StockDataFetcher()
        analyzer = NewsSentimentAnalyzer()
        print("✅ Database tables created!")
        return fetcher, analyzer
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return None, None

def populate_initial_data(fetcher, analyzer):
    """Populate database with initial stock data"""
    print("📊 Fetching initial stock data (this may take a minute)...")
    
    try:
        # Update stock data
        fetcher.update_all_stocks()
        print("✅ Stock data populated!")
        
        # Update sentiment data (with mock data if no API key)
        print("📰 Adding initial sentiment data...")
        analyzer.update_all_sentiment(fetcher.watchlist[:3])  # Just first 3 stocks to be quick
        print("✅ Sentiment data populated!")
        
    except Exception as e:
        print(f"⚠️  Warning: Some data might not have populated correctly: {e}")
        print("   You can manually update data from the dashboard sidebar.")

def create_demo_config():
    """