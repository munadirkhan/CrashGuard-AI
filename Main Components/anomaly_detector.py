import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import sqlite3
from datetime import datetime, timedelta

#CLASS to sort and calculate anomalies detected for stock (selected)
class MarketAnomalyDetector:
    def __init__(self, db_path="stock_data.db"):
        self.db_path = db_path
        self.isolation_forest = IsolationForest(
            contamination=0.1,  # Expect 10% of data to be anomalous
            random_state=42
        )
        self.scaler = StandardScaler()
    
    def calculate_technical_indicators(self, df):
        """Calculate technical indicators for anomaly detection"""
        df = df.copy()
        df = df.sort_values('date')
        
        # Price change percentage
        df['price_change_pct'] = df['close'].pct_change() * 100
        
        # Volume change percentage
        df['volume_change_pct'] = df['volume'].pct_change() * 100
        
        # Moving averages
        df['ma_5'] = df['close'].rolling(window=5).mean()
        df['ma_20'] = df['close'].rolling(window=20).mean()
        
        # Price vs MA deviation
        df['price_ma5_deviation'] = ((df['close'] - df['ma_5']) / df['ma_5']) * 100
        df['price_ma20_deviation'] = ((df['close'] - df['ma_20']) / df['ma_20']) * 100
        
        # Volatility (rolling standard deviation)
        df['volatility'] = df['price_change_pct'].rolling(window=5).std()
        
        # Volume spike indicator
        df['avg_volume_20'] = df['volume'].rolling(window=20).mean()
        df['volume_spike'] = df['volume'] / df['avg_volume_20']
        
        # Gap up/down
        df['gap'] = ((df['open'] - df['close'].shift(1)) / df['close'].shift(1)) * 100
        
        return df
    
    def detect_rule_based_anomalies(self, df):
        """Detect anomalies using simple rules"""
        anomalies = []
        
        for idx, row in df.iterrows():
            alerts = []
            severity = 0
            
            # Rule 1: Large price movement (>10% in a day)
            if abs(row.get('price_change_pct', 0)) > 10:
                alerts.append(f"Large price move: {row['price_change_pct']:.2f}%")
                severity += 2
            
            # Rule 2: Unusual volume (>3x average)
            if row.get('volume_spike', 0) > 3:
                alerts.append(f"Volume spike: {row['volume_spike']:.1f}x average")
                severity += 1
            
            # Rule 3: Gap up/down (>5%)
            if abs(row.get('gap', 0)) > 5:
                alerts.append(f"Price gap: {row['gap']:.2f}%")
                severity += 1
            
            # Rule 4: High volatility
            if row.get('volatility', 0) > 5:
                alerts.append(f"High volatility: {row['volatility']:.2f}%")
                severity += 1
            
            # Rule 5: Significant deviation from moving average
            if abs(row.get('price_ma20_deviation', 0)) > 15:
                alerts.append(f"MA deviation: {row['price_ma20_deviation']:.2f}%")
                severity += 1
            
            if alerts:
                anomalies.append({
                    'date': row['date'],
                    'symbol': row['symbol'],
                    'alerts': alerts,
                    'severity': severity,
                    'close': row['close'],
                    'volume': row['volume'],
                    'price_change_pct': row.get('price_change_pct', 0)
                })
        
        return anomalies
    
    def detect_ml_anomalies(self, df):
        """Detect anomalies using Isolation Forest"""
        if len(df) < 10:  # Need minimum data points
            return []
        
        # Prepare features for ML
        features = [
            'price_change_pct', 'volume_change_pct', 'volatility',
            'volume_spike', 'price_ma5_deviation', 'price_ma20_deviation', 'gap'
        ]
        
        # Filter out rows with NaN values
        ml_df = df[features].dropna()
        
        if len(ml_df) < 5:
            return []
        
        # Normalize features
        scaled_features = self.scaler.fit_transform(ml_df)
        
        # Detect anomalies
        anomaly_predictions = self.isolation_forest.fit_predict(scaled_features)
        
        # Get anomaly scores
        anomaly_scores = self.isolation_forest.decision_function(scaled_features)
        
        # Combine with original data
        ml_df['anomaly'] = anomaly_predictions
        ml_df['anomaly_score'] = anomaly_scores
        ml_df['date'] = df.loc[ml_df.index, 'date']
        ml_df['symbol'] = df.loc[ml_df.index, 'symbol']
        ml_df['close'] = df.loc[ml_df.index, 'close']
        ml_df['volume'] = df.loc[ml_df.index, 'volume']
        
        # Return only anomalies (prediction = -1)
        anomalies = ml_df[ml_df['anomaly'] == -1].copy()
        
        # Convert to list of dictionaries
        ml_anomalies = []
        for idx, row in anomalies.iterrows():
            ml_anomalies.append({
                'date': row['date'],
                'symbol': row['symbol'],
                'anomaly_score': row['anomaly_score'],
                'close': row['close'],
                'volume': row['volume'],
                'price_change_pct': row['price_change_pct'],
                'volume_spike': row['volume_spike']
            })
        
        return ml_anomalies
    
    def analyze_stock(self, symbol, days=30):
        """Analyze a single stock for anomalies"""
        # Get data from database
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT * FROM stock_data 
            WHERE symbol = ? 
            ORDER BY date DESC 
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(symbol, days))
        conn.close()
        
        if df.empty:
            return {'rule_based': [], 'ml_based': []}
        
        # Calculate indicators
        df = self.calculate_technical_indicators(df)
        
        # Detect anomalies
        rule_anomalies = self.detect_rule_based_anomalies(df)
        ml_anomalies = self.detect_ml_anomalies(df)
        
        return {
            'rule_based': rule_anomalies,
            'ml_based': ml_anomalies
        }
    
    def analyze_all_stocks(self):
        """Analyze all stocks in the database"""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT DISTINCT symbol FROM stock_data"
        symbols = pd.read_sql_query(query, conn)['symbol'].tolist()
        conn.close()
        
        all_anomalies = {}
        
        for symbol in symbols:
            print(f"Analyzing {symbol}...")
            anomalies = self.analyze_stock(symbol)
            if anomalies['rule_based'] or anomalies['ml_based']:
                all_anomalies[symbol] = anomalies
        
        return all_anomalies
    
    def get_top_alerts(self, limit=10):
        """Get top anomalies across all stocks"""
        all_anomalies = self.analyze_all_stocks()
        
        alerts = []
        
        for symbol, data in all_anomalies.items():
            # Add rule-based alerts
            for alert in data['rule_based']:
                alerts.append({
                    'symbol': symbol,
                    'date': alert['date'],
                    'type': 'Rule-based',
                    'severity': alert['severity'],
                    'description': '; '.join(alert['alerts']),
                    'close': alert['close'],
                    'price_change_pct': alert['price_change_pct']
                })
            
            # Add ML-based alerts
            for alert in data['ml_based']:
                alerts.append({
                    'symbol': symbol,
                    'date': alert['date'],
                    'type': 'ML-based',
                    'severity': abs(alert['anomaly_score']),  # Use absolute anomaly score as severity
                    'description': f"ML anomaly (score: {alert['anomaly_score']:.3f})",
                    'close': alert['close'],
                    'price_change_pct': alert['price_change_pct']
                })
        
        # Sort by severity and date
        alerts.sort(key=lambda x: (x['severity'], x['date']), reverse=True)
        
        return alerts[:limit]

# Usage example
if __name__ == "__main__":
    detector = MarketAnomalyDetector()
    
    # Analyze a specific stock
    aapl_anomalies = detector.analyze_stock("AAPL")
    print("AAPL Anomalies:", aapl_anomalies)
    
    # Get top alerts
    top_alerts = detector.get_top_alerts(limit=5)
    for alert in top_alerts:
        print(f"{alert['symbol']}: {alert['description']} on {alert['date']}")