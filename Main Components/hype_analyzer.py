import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from scipy import stats
from sklearn.preprocessing import MinMaxScaler
import logging

class SocialHypeAnalyzer:
    def __init__(self, db_path="stock_data.db"):
        self.db_path = db_path
        self.scaler = MinMaxScaler()
    
    def calculate_daily_hype_metrics(self, symbol, platform, date):
        """Calculate hype metrics for a specific day"""
        conn = sqlite3.connect(self.db_path)
        
        # Get posts for the day
        query = """
            SELECT sentiment_score, score, comments_count, author, mention_count, created_utc
            FROM social_posts 
            WHERE symbol = ? AND platform = ? 
            AND DATE(created_utc) = ?
        """
        
        df = pd.read_sql_query(query, conn, params=(symbol, platform, date))
        conn.close()
        
        if df.empty:
            return {
                'mention_volume': 0,
                'avg_sentiment': 0,
                'total_score': 0,
                'unique_authors': 0,
                'hype_score': 0
            }
        
        # Basic metrics
        mention_volume = len(df)
        avg_sentiment = df['sentiment_score'].mean()
        total_score = df['score'].sum()
        unique_authors = df['author'].nunique()
        
        # Advanced hype score calculation
        hype_score = self._calculate_hype_score(df)
        
        return {
            'mention_volume': mention_volume,
            'avg_sentiment': avg_sentiment,
            'total_score': total_score,
            'unique_authors': unique_authors,
            'hype_score': hype_score
        }
    
    def _calculate_hype_score(self, df):
        """Calculate a composite hype score (0-100)"""
        if df.empty:
            return 0
        
        # Components of hype score
        volume_component = min(len(df) / 10, 10)  # Volume (max 10 points)
        
        sentiment_component = max(0, df['sentiment_score'].mean() * 10)  # Sentiment (max 10 points)
        
        engagement_component = min(df['score'].sum() / 100, 10)  # Engagement (max 10 points)
        
        author_diversity = min(df['author'].nunique() / max(1, len(df)) * 10, 10)  # Diversity (max 10 points)
        
        # Time concentration bonus (posts clustered in time = higher hype)
        df['hour'] = pd.to_datetime(df['created_utc']).dt.hour
        hour_concentration = len(df) / max(1, df['hour'].nunique()) * 2  # Max 2 points
        
        # Positive sentiment bias (bullish posts count more)
        positive_bias = len(df[df['sentiment_score'] > 0.1]) / max(1, len(df)) * 3  # Max 3 points
        
        total_score = (
            volume_component + 
            sentiment_component + 
            engagement_component + 
            author_diversity + 
            hour_concentration + 
            positive_bias
        )
        
        return min(total_score, 100)  # Cap at 100
    
    def detect_hype_spikes(self, symbol, platform, days_back=30):
        """Detect unusual spikes in social hype"""
        conn = sqlite3.connect(self.db_path)
        
        # Get historical hype data
        query = """
            SELECT date, hype_score, mention_volume, avg_sentiment
            FROM social_hype_metrics 
            WHERE symbol = ? AND platform = ?
            ORDER BY date DESC 
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(symbol, platform, days_back))
        conn.close()
        
        if len(df) < 7:  # Need minimum data
            return []
        
        # Calculate rolling statistics
        df = df.sort_values('date')
        df['hype_ma_7'] = df['hype_score'].rolling(window=7).mean()
        df['hype_std_7'] = df['hype_score'].rolling(window=7).std()
        
        # Detect spikes (hype > mean + 2*std)
        spikes = []
        for idx, row in df.iterrows():
            if pd.isna(row['hype_ma_7']) or pd.isna(row['hype_std_7']):
                continue
                
            threshold = row['hype_ma_7'] + 2 * row['hype_std_7']
            
            if row['hype_score'] > threshold and row['hype_score'] > 20:  # Minimum threshold
                spike_magnitude = (row['hype_score'] - row['hype_ma_7']) / max(row['hype_std_7'], 1)
                
                spikes.append({
                    'date': row['date'],
                    'hype_score': row['hype_score'],
                    'baseline': row['hype_ma_7'],
                    'spike_magnitude': spike_magnitude,
                    'mention_volume': row['mention_volume'],
                    'avg_sentiment': row['avg_sentiment']
                })
        
        return spikes
    
    def compare_platforms(self, symbol, days_back=7):
        """Compare hype metrics across platforms"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT platform, 
                   AVG(hype_score) as avg_hype,
                   SUM(mention_volume) as total_mentions,
                   AVG(avg_sentiment) as avg_sentiment,
                   COUNT(*) as days_active
            FROM social_hype_metrics 
            WHERE symbol = ? AND date >= date('now', '-{} days')
            GROUP BY platform
        """.format(days_back)
        
        df = pd.read_sql_query(query, conn, params=(symbol,))
        conn.close()
        
        return df
    
    def correlate_with_price_movement(self, symbol, days_back=30):
        """Analyze correlation between social hype and price movements"""
        conn = sqlite3.connect(self.db_path)
        
        # Get combined social and price data
        query = """
            SELECT 
                s.date,
                s.close as price,
                s.volume as trading_volume,
                LAG(s.close, 1) OVER (ORDER BY s.date) as prev_close,
                h.hype_score,
                h.mention_volume,
                h.avg_sentiment
            FROM stock_data s
            LEFT JOIN (
                SELECT date, symbol,
                       AVG(hype_score) as hype_score,
                       SUM(mention_volume) as mention_volume,
                       AVG(avg_sentiment) as avg_sentiment
                FROM social_hype_metrics 
                WHERE platform IN ('reddit', 'twitter')
                GROUP BY date, symbol
            ) h ON s.date = h.date AND s.symbol = h.symbol
            WHERE s.symbol = ?
            ORDER BY s.date DESC
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(symbol, days_back))
        conn.close()
        
        if df.empty or len(df) < 10:
            return {'correlations': {}, 'signals': []}
        
        # Calculate price change
        df['price_change_pct'] = ((df['price'] - df['prev_close']) / df['prev_close'] * 100).fillna(0)
        
        # Fill missing hype data
        df['hype_score'] = df['hype_score'].fillna(0)
        df['mention_volume'] = df['mention_volume'].fillna(0)
        df['avg_sentiment'] = df['avg_sentiment'].fillna(0)
        
        # Calculate correlations
        correlations = {
            'hype_vs_price': df['hype_score'].corr(df['price_change_pct']),
            'mentions_vs_price': df['mention_volume'].corr(df['price_change_pct']),
            'sentiment_vs_price': df['avg_sentiment'].corr(df['price_change_pct']),
            'hype_vs_volume': df['hype_score'].corr(df['trading_volume'])
        }
        
        # Find potential signals (high hype followed by price movement)
        signals = self._find_predictive_signals(df)
        
        return {
            'correlations': correlations,
            'signals': signals,
            'data': df
        }
    
    def _find_predictive_signals(self, df):
        """Find instances where social hype predicted price movements"""
        signals = []
        df = df.sort_values('date')
        
        for i in range(1, len(df)):
            current = df.iloc[i]
            previous = df.iloc[i-1]
            
            # Look for high hype followed by significant price movement
            hype_threshold = df['hype_score'].quantile(0.8)  # Top 20% hype
            price_change_threshold = 5  # 5% price change
            
            if (previous['hype_score'] > hype_threshold and 
                abs(current['price_change_pct']) > price_change_threshold):
                
                signals.append({
                    'signal_date': previous['date'],
                    'move_date': current['date'],
                    'hype_score': previous['hype_score'],
                    'mention_volume': previous['mention_volume'],
                    'sentiment': previous['avg_sentiment'],
                    'price_change': current['price_change_pct'],
                    'prediction_accuracy': 'correct' if (
                        (previous['avg_sentiment'] > 0.1 and current['price_change_pct'] > 0) or
                        (previous['avg_sentiment'] < -0.1 and current['price_change_pct'] < 0)
                    ) else 'incorrect'
                })
        
        return signals
    
    def update_hype_metrics(self, symbol=None, date=None):
        """Update daily hype metrics for stocks"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        
        # Get symbols to update
        if symbol:
            symbols = [symbol]
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT symbol FROM social_posts")
            symbols = [row[0] for row in cursor.fetchall()]
        
        platforms = ['reddit', 'twitter']
        
        for sym in symbols:
            for platform in platforms:
                metrics = self.calculate_daily_hype_metrics(sym, platform, date)
                
                # Save to database
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO social_hype_metrics 
                        (symbol, date, platform, mention_volume, avg_sentiment, 
                         total_score, unique_authors, hype_score, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sym, date, platform, metrics['mention_volume'],
                        metrics['avg_sentiment'], metrics['total_score'],
                        metrics['unique_authors'], metrics['hype_score'],
                        datetime.now().isoformat()
                    ))
                except Exception as e:
                    print(f"Error updating metrics for {sym}/{platform}: {e}")
        
        conn.commit()
        conn.close()
        print(f"✅ Updated hype metrics for {date}")
    
    def get_hype_summary(self, symbol, days=7):
        """Get hype summary for a symbol"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT date, platform, hype_score, mention_volume, avg_sentiment
            FROM social_hype_metrics 
            WHERE symbol = ? AND date >= date('now', '-{} days')
            ORDER BY date DESC, hype_score DESC
        """.format(days)
        
        df = pd.read_sql_query(query, conn, params=(symbol,))
        conn.close()
        
        if df.empty:
            return {
                'current_hype': 0,
                'trend': 'neutral',
                'peak_day': None,
                'platform_breakdown': {}
            }
        
        # Calculate summary stats
        current_hype = df['hype_score'].iloc[0] if not df.empty else 0
        
        # Determine trend
        if len(df) >= 2:
            recent_avg = df.head(3)['hype_score'].mean()
            older_avg = df.tail(3)['hype_score'].mean()
            trend = 'rising' if recent_avg > older_avg * 1.2 else 'falling' if recent_avg < older_avg * 0.8 else 'stable'
        else:
            trend = 'insufficient_data'
        
        # Find peak day
        peak_day = df.loc[df['hype_score'].idxmax()] if not df.empty else None
        
        # Platform breakdown
        platform_breakdown = df.groupby('platform').agg({
            'hype_score': 'mean',
            'mention_volume': 'sum',
            'avg_sentiment': 'mean'
        }).to_dict('index')
        
        return {
            'current_hype': current_hype,
            'trend': trend,
            'peak_day': peak_day.to_dict() if peak_day is not None else None,
            'platform_breakdown': platform_breakdown,
            'recent_data': df.head(10).to_dict('records')
        }
    
    def generate_hype_alerts(self, min_hype_score=30):
        """Generate alerts for high hype stocks"""
        conn = sqlite3.connect(self.db_path)
        
        # Get recent high-hype stocks
        query = """
            SELECT symbol, MAX(hype_score) as max_hype, 
                   AVG(mention_volume) as avg_mentions,
                   AVG(avg_sentiment) as avg_sentiment,
                   COUNT(*) as days_active
            FROM social_hype_metrics 
            WHERE date >= date('now', '-3 days')
            GROUP BY symbol
            HAVING max_hype >= ?
            ORDER BY max_hype DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(min_hype_score,))
        conn.close()
        
        alerts = []
        for _, row in df.iterrows():
            alert_level = 'HIGH' if row['max_hype'] > 60 else 'MEDIUM' if row['max_hype'] > 40 else 'LOW'
            
            alerts.append({
                'symbol': row['symbol'],
                'alert_level': alert_level,
                'hype_score': row['max_hype'],
                'avg_mentions': row['avg_mentions'],
                'sentiment': row['avg_sentiment'],
                'description': f"Social hype spike detected: {row['max_hype']:.1f}/100"
            })
        
        return alerts

# Usage example
if __name__ == "__main__":
    analyzer = SocialHypeAnalyzer()
    
    # Update metrics for today
    analyzer.update_hype_metrics()
    
    # Get hype summary for PHH
    summary = analyzer.get_hype_summary("PHH", days=7)
    print("PHH Hype Summary:", summary)
    
    # Detect hype spikes
    spikes = analyzer.detect_hype_spikes("PHH", "reddit", days_back=30)
    print(f"Found {len(spikes)} hype spikes for PHH")
    
    # Analyze correlation with price
    correlation = analyzer.correlate_with_price_movement("PHH", days_back=30)
    print("Correlations:", correlation['correlations'])