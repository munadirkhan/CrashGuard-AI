#!/usr/bin/env python3
"""
Local PC Setup Script for Market Signal MVP
Handles all downloads, installations, and initial setup
"""

import os
import sys
import subprocess
import sqlite3
import time
from datetime import datetime

def print_step(step, description):
    """Pretty print setup steps"""
    print(f"\n🔧 Step {step}: {description}")
    print("-" * 50)

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - Compatible!")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Need Python 3.8+")
        print("   Please install Python 3.8 or higher from python.org")
        return False

def install_packages():
    """Install all required packages"""
    print("📦 Installing required packages...")
    print("   This may take 5-10 minutes depending on your internet connection...")
    
    packages = [
        "streamlit==1.28.0",
        "yfinance==0.2.18", 
        "pandas==2.1.0",
        "numpy==1.25.2",
        "plotly==5.15.0",
        "scikit-learn==1.3.0",
        "requests==2.31.0",
        "vaderSentiment==3.3.2",
        "praw==7.7.0",
        "tweepy==4.14.0",
        "scipy==1.11.0"
    ]
    
    failed_packages = []
    
    for package in packages:
        print(f"   📥 Installing {package.split('==')[0]}...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"   ✅ {package.split('==')[0]} installed successfully")
        except subprocess.CalledProcessError:
            print(f"   ❌ Failed to install {package}")
            failed_packages.append(package)
    
    if failed_packages:
        print(f"\n⚠️ Failed to install: {', '.join(failed_packages)}")
        print("   Try running manually: pip install package-name")
        return False
    else:
        print("\n✅ All packages installed successfully!")
        return True

def create_project_structure():
    """Create necessary directories and files"""
    print("📁 Creating project structure...")
    
    # Create directories
    dirs_to_create = [".streamlit", "data", "logs"]
    
    for dir_name in dirs_to_create:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"   ✅ Created directory: {dir_name}")
    
    # Create streamlit config
    streamlit_config = """
[theme]
base = "light"
primaryColor = "#ff6b6b"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"

[server]
headless = true
port = 8501
"""
    
    config_path = ".streamlit/config.toml"
    with open(config_path, 'w') as f:
        f.write(streamlit_config.strip())
    print(f"   ✅ Created Streamlit config: {config_path}")
    
    # Create secrets template (for later API setup)
    secrets_template = """# Add your API keys here when ready
# NEWS_API_KEY = "your_newsapi_key_here"
# REDDIT_CLIENT_ID = "your_reddit_client_id"
# REDDIT_CLIENT_SECRET = "your_reddit_secret"
# TWITTER_BEARER_TOKEN = "your_twitter_token"
"""
    
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        with open(secrets_path, 'w') as f:
            f.write(secrets_template.strip())
        print(f"   ✅ Created secrets template: {secrets_path}")

def initialize_database():
    """Initialize SQLite database with tables"""
    print("🗄️ Initializing database...")
    
    try:
        # Import our modules to initialize database
        from data_fetcher import StockDataFetcher
        from social_data_fetcher import SocialDataFetcher
        
        # Initialize components (this creates tables)
        stock_fetcher = StockDataFetcher()
        social_fetcher = SocialDataFetcher()
        
        print("   ✅ Database tables created successfully")
        
        # Populate with some initial stock data
        print("   📊 Fetching initial stock data...")
        stock_fetcher.update_all_stocks()
        print("   ✅ Initial stock data loaded")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database initialization failed: {e}")
        return False

def test_core_functionality():
    """Test that everything is working"""
    print("🧪 Testing core functionality...")
    
    try:
        # Test stock data
        from data_fetcher import StockDataFetcher
        fetcher = StockDataFetcher()
        data = fetcher.get_latest_prices()
        
        if not data.empty:
            print(f"   ✅ Stock data working - {len(data)} stocks loaded")
        else:
            print("   ⚠️ No stock data found")
        
        # Test anomaly detection
        from anomaly_detector import MarketAnomalyDetector
        detector = MarketAnomalyDetector()
        alerts = detector.get_top_alerts(limit=5)
        print(f"   ✅ Anomaly detection working - {len(alerts)} alerts generated")
        
        # Test social components (with mock data)
        from social_data_fetcher import SocialDataFetcher
        social = SocialDataFetcher()
        posts = social.fetch_all_social_data("AAPL", hours_back=24)
        print(f"   ✅ Social analysis working - {len(posts)} posts analyzed")
        
        # Test dashboard imports
        import streamlit
        import plotly
        print("   ✅ Dashboard components ready")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_launch_script():
    """Create easy launch script"""
    print("🚀 Creating launch scripts...")
    
    # Windows batch file
    windows_script = """@echo off
echo Starting Market Signal MVP Dashboard...
echo Opening in your browser in 5 seconds...
timeout /t 5 /nobreak > nul
start http://localhost:8501
streamlit run enhanced_app.py
pause
"""
    
    with open("launch_dashboard.bat", 'w') as f:
        f.write(windows_script)
    print("   ✅ Created Windows launcher: launch_dashboard.bat")
    
    # Mac/Linux shell script
    unix_script = """#!/bin/bash
echo "Starting Market Signal MVP Dashboard..."
echo "Opening in your browser in 5 seconds..."
sleep 5
if command -v open > /dev/null; then
    open http://localhost:8501
elif command -v xdg-open > /dev/null; then
    xdg-open http://localhost:8501
fi
streamlit run enhanced_app.py
"""
    
    with open("launch_dashboard.sh", 'w') as f:
        f.write(unix_script)
    
    # Make executable on Unix systems
    try:
        os.chmod("launch_dashboard.sh", 0o755)
        print("   ✅ Created Unix launcher: launch_dashboard.sh")
    except:
        print("   ✅ Created Unix launcher: launch_dashboard.sh (run: chmod +x launch_dashboard.sh)")

def create_readme():
    """Create README for the project"""
    readme_content = f"""# Market Signal MVP - Local Installation

## 🎉 Setup Complete!

Your Market Signal MVP is now installed and ready to use.

### Quick Start

**Windows Users:**
```
Double-click: launch_dashboard.bat
```

**Mac/Linux Users:**
```bash
./launch_dashboard.sh
```

**Manual Launch:**
```bash
streamlit run enhanced_app.py
```

### What You Can Do Right Now

✅ **Monitor 10 popular stocks** (AAPL, TSLA, GOOGL, etc.)  
✅ **Detect price/volume anomalies** using ML algorithms  
✅ **Analyze social sentiment** (currently using mock data)  
✅ **View interactive dashboards** with real-time charts  
✅ **Generate trading signals** based on multiple factors  
✅ **Backtest strategies** on historical data  

### Dashboard Features

1. **🎯 Overview** - Market alerts and heatmaps
2. **📈 Stock Analysis** - Detailed price charts with indicators  
3. **📱 Social Signals** - Reddit/Twitter sentiment analysis
4. **🔗 Correlation Analysis** - Social vs price relationships
5. **🤖 Trading Signals** - AI-powered predictions

### Adding Real Social Data (Optional)

To get real Reddit/Twitter data instead of mock data:

1. Get API keys from:
   - NewsAPI: https://newsapi.org (free)
   - Reddit: https://www.reddit.com/prefs/apps (free)
   - Twitter: https://developer.twitter.com (free tier)

2. Add keys to `.streamlit/secrets.toml`

3. Restart dashboard

### Files Created

- `stock_data.db` - Local database with stock and social data
- `.streamlit/` - Dashboard configuration
- `launch_dashboard.*` - Easy launch scripts

### Need Help?

- Dashboard not loading? Wait 30 seconds after launch
- Data issues? Check your internet connection
- API errors? Review the console output

### Setup completed on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Happy trading! 📈🚀
"""
    
    with open("README_LOCAL.md", 'w') as f:
        f.write(readme_content)
    print("   ✅ Created local README: README_LOCAL.md")

def main():
    """Main setup function"""
    print("🚀 Market Signal MVP - Local PC Setup")
    print("=" * 60)
    print("This will download and install everything needed to run your dashboard locally.")
    print("Estimated time: 5-10 minutes")
    print("=" * 60)
    
    # Step 1: Check Python
    print_step(1, "Checking Python Version")
    if not check_python_version():
        return False
    
    # Step 2: Install packages
    print_step(2, "Installing Required Packages")
    if not install_packages():
        print("\n❌ Package installation failed. Please check your internet connection.")
        return False
    
    # Step 3: Create project structure
    print_step(3, "Setting Up Project Structure")
    create_project_structure()
    
    # Step 4: Initialize database
    print_step(4, "Initializing Database & Loading Data")
    if not initialize_database():
        print("\n❌ Database setup failed. Please check the error messages above.")
        return False
    
    # Step 5: Test functionality
    print_step(5, "Testing Core Functionality")
    if not test_core_functionality():
        print("\n❌ Core functionality test failed. Please review error messages.")
        return False
    
    # Step 6: Create launch scripts
    print_step(6, "Creating Launch Scripts")
    create_launch_script()
    create_readme()
    
    # Success message
    print("\n" + "=" * 60)
    print("🎉 SUCCESS! Market Signal MVP is ready!")
    print("=" * 60)
    print("\n📋 What was installed:")
    print("   • All Python packages (Streamlit, ML libraries, etc.)")
    print("   • SQLite database with initial stock data")
    print("   • Dashboard configuration")
    print("   • Launch scripts for easy startup")
    
    print("\n🚀 To start your dashboard:")
    print("   Windows: Double-click 'launch_dashboard.bat'")
    print("   Mac/Linux: Run './launch_dashboard.sh'")
    print("   Manual: Run 'streamlit run enhanced_app.py'")
    
    print("\n📱 Dashboard will open at: http://localhost:8501")
    print("\n💡 Next steps:")
    print("   1. Test the dashboard with mock data")
    print("   2. (Optional) Add API keys for real social data")
    print("   3. Push to GitHub when ready")
    
    print("\n📖 Check 'README_LOCAL.md' for detailed usage instructions")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Setup cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error during setup: {e}")
        print("Please check your Python installation and internet connection")
        import traceback
        traceback.print_exc()