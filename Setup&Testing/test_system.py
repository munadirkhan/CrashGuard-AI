#!/usr/bin/env python3
"""
Quick System Test - Market Signal MVP
Tests all components without requiring API keys
"""

import sys
import traceback
from datetime import datetime

def test_data_fetcher():
    """Test stock data fetching"""
    print("🧪 Testing Stock Data Fetcher...")
    try:
        from data_fetcher import StockDataFetcher
        fetcher = StockDataFetcher()
        
        # Test with a single stock
        data = fetcher.fetch_stock_data("AAPL", period="5d")
        if data is not None and not data.empty:
            print(f"   ✅ Successfully fetched {len(data)} records for AAPL")
            
            # Test database save
            fetcher.save_to_database(data, "AAPL")
            print("   ✅ Database save successful")
            
            # Test data retrieval
            retrieved = fetcher.get_stock_data("AAPL", days=5)
            print(f"   ✅ Retrieved {len(retrieved)} records from database")
            
            return True
        else:
            print("   ❌ No data retrieved")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False

def test_anomaly_detector():
    """Test anomaly detection"""
    print("🧪 Testing Anomaly Detector...")
    try:
        from anomaly_detector import MarketAnomalyDetector
        detector = MarketAnomalyDetector()
        
        # Analyze AAPL (should have data from previous test)
        anomalies = detector.analyze_stock("AAPL", days=5)
        
        rule_count = len(anomalies.get('rule_based', []))
        ml_count = len(anomalies.get('ml_based', []))
        
        print(f"   ✅ Found {rule_count} rule-based and {ml_count} ML anomalies")
        
        # Test top alerts
        alerts = detector.get_top_alerts(limit=3)
        print(f"   ✅ Generated {len(alerts)} top alerts")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False

def test_social_fetcher():
    """Test social media fetcher (mock data)"""
    print("🧪 Testing Social Media Fetcher...")
    try:
        from social_data_fetcher import SocialDataFetcher
        fetcher = SocialDataFetcher()
        
        # Test with mock data (no API keys needed)
        posts = fetcher.fetch_all_social_data("PHH", hours_back=24)
        
        print(f"   ✅ Fetched {len(posts)} social media posts (mock data)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False

def test_hype_analyzer():
    """Test social hype analysis"""
    print("🧪 Testing Hype Analyzer...")
    try:
        from hype_analyzer import SocialHypeAnalyzer
        analyzer = SocialHypeAnalyzer()
        
        # Update metrics for today
        analyzer.update_hype_metrics("PHH")
        
        # Get summary
        summary = analyzer.get_hype_summary("PHH", days=7)
        
        print(f"   ✅ Hype analysis complete - Current hype: {summary['current_hype']:.1f}")
        print(f"   ✅ Trend: {summary['trend']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False

def test_correlation_engine():
    """Test social-price correlation"""
    print("🧪 Testing Correlation Engine...")
    try:
        from correlation_engine import SocialPriceCorrelationEngine
        engine = SocialPriceCorrelationEngine()
        
        # Test with PHH (should have some social data)
        signals = engine.generate_trading_signals("PHH")
        
        if 'error' not in signals:
            print(f"   ✅ Generated trading signals - Overall: {signals.get('overall_signal', 'UNKNOWN')}")
            print(f"   ✅ Signal strength: {signals.get('signal_strength', 0):.0f}/100")
        else:
            print(f"   ⚠️ Signal generation returned: {signals['error']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False

def test_dashboard_import():
    """Test dashboard imports"""
    print("🧪 Testing Dashboard Components...")
    try:
        import streamlit as st
        print("   ✅ Streamlit imported successfully")
        
        import plotly.graph_objects as go
        print("   ✅ Plotly imported successfully")
        
        # Test enhanced dashboard imports
        from enhanced_app import initialize_components
        print("   ✅ Enhanced dashboard components importable")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False

def test_backtester():
    """Test backtesting engine"""
    print("🧪 Testing Backtesting Engine...")
    try:
        from backtest_engine import SocialTradingBacktester
        backtester = SocialTradingBacktester(initial_capital=10000)
        
        print("   ✅ Backtester initialized successfully")
        
        # Test data generation (don't run full backtest in quick test)
        start_date = "2024-01-01"
        end_date = "2024-01-10"
        
        social_data = backtester.generate_historical_social_data("AAPL", start_date, end_date)
        
        if not social_data.empty:
            print(f"   ✅ Generated {len(social_data)} days of mock social data")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False

def run_full_test():
    """Run complete system test"""
    print("🚀 Market Signal MVP - System Test")
    print("=" * 50)
    
    tests = [
        ("Stock Data Fetcher", test_data_fetcher),
        ("Anomaly Detector", test_anomaly_detector),
        ("Social Media Fetcher", test_social_fetcher),
        ("Hype Analyzer", test_hype_analyzer),
        ("Correlation Engine", test_correlation_engine),
        ("Dashboard Components", test_dashboard_import),
        ("Backtesting Engine", test_backtester),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ Critical error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Your system is ready to run.")
        print("\nNext steps:")
        print("1. Get API keys (optional for basic functionality)")
        print("2. Run: streamlit run enhanced_app.py")
        print("3. Start collecting data and analyzing!")
    elif passed >= total * 0.7:
        print("\n👍 Most tests passed! System should work with minor issues.")
        print("Review failed tests above and fix any import/dependency issues.")
    else:
        print("\n⚠️ Multiple test failures detected.")
        print("Please check your Python environment and install missing packages:")
        print("pip install -r requirements.txt")

if __name__ == "__main__":
    run_full_test()