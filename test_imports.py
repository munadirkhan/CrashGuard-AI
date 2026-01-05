#!/usr/bin/env python3
"""
Quick test to verify all imports work
"""
import sys
import os

# Add Main Components to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Main Components'))

print("Testing imports...")
print("-" * 50)

try:
    from data_fetcher import StockDataFetcher
    print("✅ data_fetcher.py imports OK")
except Exception as e:
    print(f"❌ data_fetcher.py ERROR: {e}")

try:
    from anomaly_detector import MarketAnomalyDetector
    print("✅ anomaly_detector.py imports OK")
except Exception as e:
    print(f"❌ anomaly_detector.py ERROR: {e}")

try:
    from sentiment_analyzer import NewsSentimentAnalyzer
    print("✅ sentiment_analyzer.py imports OK")
except Exception as e:
    print(f"❌ sentiment_analyzer.py ERROR: {e}")

try:
    from social_data_fetcher import SocialDataFetcher
    print("✅ social_data_fetcher.py imports OK")
except Exception as e:
    print(f"❌ social_data_fetcher.py ERROR: {e}")

try:
    from hype_analyzer import SocialHypeAnalyzer
    print("✅ hype_analyzer.py imports OK")
except Exception as e:
    print(f"❌ hype_analyzer.py ERROR: {e}")

try:
    from correlation_engine import SocialPriceCorrelationEngine
    print("✅ correlation_engine.py imports OK")
except Exception as e:
    print(f"❌ correlation_engine.py ERROR: {e}")

try:
    from backtest_engine import SocialTradingBacktester
    print("✅ backtest_engine.py imports OK")
except Exception as e:
    print(f"❌ backtest_engine.py ERROR: {e}")

print("-" * 50)
print("Import test complete!")
