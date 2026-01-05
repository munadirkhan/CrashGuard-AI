import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

class SocialPriceCorrelationEngine:
    def __init__(self, db_path="stock_data.db"):
        self.db_path = db_path
        self.prediction_models = {}
        
    def get_combined_data(self, symbol, days_back=60):
        """Get combined social and price data for analysis"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT 
            s.date,
            s.open, s.high, s.low, s.close, s.volume as trading_volume,
            LAG(s.close, 1) OVER (ORDER BY s.date) as prev_close,
            LAG(s.close, 2) OVER (ORDER BY s.date) as prev_close_2,
            -- Social metrics (aggregated across platforms)
            COALESCE(h.total_hype, 0) as hype_score,
            COALESCE(h.total_mentions, 0) as mention_volume,
            COALESCE(h.avg_sentiment, 0) as avg_sentiment,
            COALESCE(h.unique_authors, 0) as unique_authors,
            -- Lagged social metrics (previous day)
            LAG(COALESCE(h.total_hype, 0), 1) OVER (ORDER BY s.date) as prev_hype,
            LAG(COALESCE(h.total_mentions, 0), 1) OVER (ORDER BY s.date) as prev_mentions,
            LAG(COALESCE(h.avg_sentiment, 0), 1) OVER (ORDER BY s.date) as prev_sentiment
        FROM stock_data s
        LEFT JOIN (
            SELECT 
                date, symbol,
                SUM(hype_score) as total_hype,
                SUM(mention_volume) as total_mentions,
                AVG(avg_sentiment) as avg_sentiment,
                SUM(unique_authors) as unique_authors
            FROM social_hype_metrics 
            GROUP BY date, symbol
        ) h ON s.date = h.date AND s.symbol = h.symbol
        WHERE s.symbol = ?
        ORDER BY s.date DESC
        LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(symbol, days_back))
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        # Calculate derived features
        df = df.sort_values('date')
        
        # Price features
        df['price_change_pct'] = ((df['close'] - df['prev_close']) / df['prev_close'] * 100).fillna(0)
        df['price_change_2d'] = ((df['close'] - df['prev_close_2']) / df['prev_close_2'] * 100).fillna(0)
        df['volatility'] = df['price_change_pct'].rolling(window=5).std().fillna(0)
        df['volume_ratio'] = (df['trading_volume'] / df['trading_volume'].rolling(window=20).mean()).fillna(1)
        
        # Social features
        df['hype_momentum'] = df['hype_score'] - df['prev_hype']
        df['mention_momentum'] = df['mention_volume'] - df['prev_mentions']
        df['sentiment_shift'] = df['avg_sentiment'] - df['prev_sentiment']
        
        # Rolling social averages
        df['hype_ma_3'] = df['hype_score'].rolling(window=3).mean().fillna(0)
        df['hype_ma_7'] = df['hype_score'].rolling(window=7).mean().fillna(0)
        df['mentions_ma_3'] = df['mention_volume'].rolling(window=3).mean().fillna(0)
        
        return df
    
    def analyze_lead_lag_relationships(self, symbol, max_lag_days=5):
        """Analyze if social signals lead or lag price movements"""
        df = self.get_combined_data(symbol, days_back=90)
        
        if len(df) < max_lag_days * 2:
            return {'error': 'Insufficient data'}
        
        correlations = {}
        
        # Test different lag periods
        for lag in range(-max_lag_days, max_lag_days + 1):
            if lag == 0:
                social_col = 'hype_score'
                price_col = 'price_change_pct'
            elif lag > 0:
                # Social leads price by 'lag' days
                social_col = 'hype_score'
                price_col = f'price_change_pct_lag_{lag}'
                df[price_col] = df['price_change_pct'].shift(-lag)
            else:
                # Price leads social by abs(lag) days
                social_col = f'hype_score_lag_{abs(lag)}'
                price_col = 'price_change_pct'
                df[social_col] = df['hype_score'].shift(-abs(lag))
            
            # Calculate correlation
            if social_col in df.columns and price_col in df.columns:
                valid_data = df[[social_col, price_col]].dropna()
                if len(valid_data) > 10:
                    corr, p_value = pearsonr(valid_data[social_col], valid_data[price_col])
                    correlations[lag] = {'correlation': corr, 'p_value': p_value, 'n': len(valid_data)}
        
        # Find optimal lag
        best_lag = max(correlations.keys(), key=lambda x: abs(correlations[x]['correlation'])) if correlations else 0
        
        return {
            'correlations_by_lag': correlations,
            'optimal_lag_days': best_lag,
            'optimal_correlation': correlations.get(best_lag, {}).get('correlation', 0),
            'interpretation': self._interpret_lag(best_lag, correlations.get(best_lag, {}).get('correlation', 0))
        }
    
    def _interpret_lag(self, lag, correlation):
        """Interpret the lag relationship"""
        if abs(correlation) < 0.1:
            return "No significant correlation detected"
        elif lag > 0:
            return f"Social signals LEAD price movements by {lag} days (correlation: {correlation:.3f})"
        elif lag < 0:
            return f"Price movements LEAD social signals by {abs(lag)} days (correlation: {correlation:.3f})"
        else:
            return f"Social signals and price movements are simultaneous (correlation: {correlation:.3f})"
    
    def build_prediction_model(self, symbol, model_type='random_forest'):
        """Build a model to predict price movements from social signals"""
        df = self.get_combined_data(symbol, days_back=90)
        
        if len(df) < 30:
            return {'error': 'Insufficient data for model training'}
        
        # Define features and target
        feature_columns = [
            'prev_hype', 'prev_mentions', 'prev_sentiment',
            'hype_momentum', 'mention_momentum', 'sentiment_shift',
            'hype_ma_3', 'mentions_ma_3', 'volatility', 'volume_ratio'
        ]
        
        # Clean data
        model_df = df[feature_columns + ['price_change_pct']].dropna()
        
        if len(model_df) < 20:
            return {'error': 'Insufficient clean data for modeling'}
        
        X = model_df[feature_columns]
        y = model_df['price_change_pct']
        
        # Split data (80% train, 20% test)
        split_idx = int(len(model_df) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Train model
        if model_type == 'random_forest':
            model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
        else:
            model = LinearRegression()
        
        model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Feature importance (for Random Forest)
        feature_importance = {}
        if hasattr(model, 'feature_importances_'):
            feature_importance = dict(zip(feature_columns, model.feature_importances_))
            feature_importance = {k: float(v) for k, v in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)}
        
        # Store model
        self.prediction_models[symbol] = model
        
        return {
            'model_type': model_type,
            'mae': mae,
            'r2_score': r2,
            'feature_importance': feature_importance,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'model_stored': True
        }
    
    def predict_next_day_movement(self, symbol):
        """Predict next day's price movement using social signals"""
        if symbol not in self.prediction_models:
            model_result = self.build_prediction_model(symbol)
            if 'error' in model_result:
                return model_result
        
        # Get latest data
        df = self.get_combined_data(symbol, days_back=10)
        
        if df.empty:
            return {'error': 'No recent data available'}
        
        latest_data = df.iloc[-1]
        
        # Prepare features
        feature_columns = [
            'prev_hype', 'prev_mentions', 'prev_sentiment',
            'hype_momentum', 'mention_momentum', 'sentiment_shift',
            'hype_ma_3', 'mentions_ma_3', 'volatility', 'volume_ratio'
        ]
        
        features = []
        for col in feature_columns:
            features.append(latest_data.get(col, 0))
        
        # Make prediction
        model = self.prediction_models[symbol]
        prediction = model.predict([features])[0]
        
        # Calculate confidence based on recent model performance
        confidence = min(abs(prediction) / 5.0, 1.0)  # Simple confidence metric based on simple prediction model accuracy is low
        
        return {
            'predicted_change_pct': prediction,
            'confidence': confidence,
            'direction': 'UP' if prediction > 0.5 else 'DOWN' if prediction < -0.5 else 'NEUTRAL',
            'current_social_signals': {
                'hype_score': latest_data.get('hype_score', 0),
                'mention_volume': latest_data.get('mention_volume', 0),
                'avg_sentiment': latest_data.get('avg_sentiment', 0)
            }
        }
    
    def detect_social_price_divergence(self, symbol, days_back=14):
        """Detect when social sentiment diverges from price action"""
        df = self.get_combined_data(symbol, days_back=days_back)
        
        if len(df) < 7:
            return {'error': 'Insufficient data'}
        
        # Calculate recent trends
        recent_df = df.tail(7)
        
        # Price trend
        price_trend = recent_df['price_change_pct'].mean()
        price_direction = 'bullish' if price_trend > 1 else 'bearish' if price_trend < -1 else 'neutral'
        
        # Social sentiment trend  
        sentiment_trend = recent_df['avg_sentiment'].mean()
        sentiment_direction = 'bullish' if sentiment_trend > 0.1 else 'bearish' if sentiment_trend < -0.1 else 'neutral'
        
        # Hype trend
        hype_trend = recent_df['hype_score'].diff().mean()
        hype_direction = 'increasing' if hype_trend > 5 else 'decreasing' if hype_trend < -5 else 'stable'
        
        # Detect divergences
        divergences = []
        
        if price_direction == 'bearish' and sentiment_direction == 'bullish':
            divergences.append("Bullish social sentiment despite bearish price action - potential reversal signal")
        
        if price_direction == 'bullish' and sentiment_direction == 'bearish':
            divergences.append("Bearish social sentiment despite bullish price action - potential weakness")
        
        if hype_direction == 'increasing' and price_direction == 'bearish':
            divergences.append("Rising social hype with falling prices - potential accumulation")
        
        if hype_direction == 'decreasing' and price_direction == 'bullish':
            divergences.append("Declining social interest despite rising prices - potential lack of sustainability")
        
        return {
            'price_trend': {'direction': price_direction, 'avg_change': price_trend},
            'sentiment_trend': {'direction': sentiment_direction, 'avg_sentiment': sentiment_trend},
            'hype_trend': {'direction': hype_direction, 'avg_change': hype_trend},
            'divergences': divergences,
            'divergence_count': len(divergences)
        }
    
    def generate_trading_signals(self, symbol):
        """Generate trading signals based on social-price correlation"""
        # Get prediction
        prediction = self.predict_next_day_movement(symbol)
        
        # Get divergence analysis
        divergence = self.detect_social_price_divergence(symbol)
        
        # Get lead-lag analysis
        lead_lag = self.analyze_lead_lag_relationships(symbol)
        
        # Get recent data
        df = self.get_combined_data(symbol, days_back=5)
        
        if df.empty:
            return {'error': 'No data available'}
        
        latest = df.iloc[-1]
        
        signals = []
        signal_strength = 0
        
        # Signal 1: Prediction-based
        if 'predicted_change_pct' in prediction:
            if prediction['predicted_change_pct'] > 2 and prediction['confidence'] > 0.6:
                signals.append(f"BUY signal: Model predicts +{prediction['predicted_change_pct']:.1f}% move")
                signal_strength += prediction['confidence'] * 30
            elif prediction['predicted_change_pct'] < -2 and prediction['confidence'] > 0.6:
                signals.append(f"SELL signal: Model predicts {prediction['predicted_change_pct']:.1f}% move")
                signal_strength += prediction['confidence'] * 30
        
        # Signal 2: Divergence-based
        if 'divergences' in divergence and divergence['divergences']:
            for div in divergence['divergences']:
                if 'reversal' in div:
                    signals.append(f"REVERSAL signal: {div}")
                    signal_strength += 20
                else:
                    signals.append(f"CAUTION: {div}")
                    signal_strength += 10
        
        # Signal 3: Hype spike
        current_hype = latest.get('hype_score', 0)
        if current_hype > 50:
            signals.append(f"HIGH HYPE alert: Score {current_hype:.1f}/100 - monitor for volatility")
            signal_strength += 15
        
        # Signal 4: Social momentum
        hype_momentum = latest.get('hype_momentum', 0)
        if abs(hype_momentum) > 20:
            direction = "increasing" if hype_momentum > 0 else "decreasing"
            signals.append(f"Social momentum {direction}: {abs(hype_momentum):.1f} point change")
            signal_strength += 10
        
        # Overall signal classification
        if signal_strength > 50:
            overall_signal = 'STRONG'
        elif signal_strength > 25:
            overall_signal = 'MODERATE'
        elif signal_strength > 10:
            overall_signal = 'WEAK'
        else:
            overall_signal = 'NO SIGNAL'
        
        return {
            'symbol': symbol,
            'overall_signal': overall_signal,
            'signal_strength': signal_strength,
            'individual_signals': signals,
            'prediction_data': prediction,
            'divergence_data': divergence,
            'lead_lag_data': lead_lag,
            'current_metrics': {
                'hype_score': current_hype,
                'sentiment': latest.get('avg_sentiment', 0),
                'mentions': latest.get('mention_volume', 0)
            }
        }

    def rank_bullish_candidates(self, symbols, days_back=30, top_n=5):
        """Rank symbols by bullish composite score using social + price momentum."""
        rankings = []
        for symbol in symbols:
            df = self.get_combined_data(symbol, days_back)
            if df.empty:
                continue
            latest = df.iloc[-1]

            hype = latest.get('hype_score', 0) / 100
            sentiment = max(0, latest.get('avg_sentiment', 0))  # focus on positive
            mentions = latest.get('mention_volume', 0)
            mention_mom = max(0, latest.get('mention_momentum', 0))
            price_mom = max(0, latest.get('price_change_2d', 0)) / 100
            vol_ratio = min(3, latest.get('volume_ratio', 1)) / 3

            score = (
                0.35 * hype +
                0.25 * sentiment +
                0.15 * (mention_mom / 1000) +
                0.15 * price_mom +
                0.10 * vol_ratio
            )

            rankings.append({
                'symbol': symbol,
                'score': score,
                'hype': latest.get('hype_score', 0),
                'sentiment': latest.get('avg_sentiment', 0),
                'mentions': mentions,
                'mention_momentum': mention_mom,
                'price_change_2d': latest.get('price_change_2d', 0),
                'volume_ratio': latest.get('volume_ratio', 1)
            })

        rankings = sorted(rankings, key=lambda x: x['score'], reverse=True)
        return rankings[:top_n]

# Usage example
if __name__ == "__main__":
    engine = SocialPriceCorrelationEngine()
    
    # Analyze PHH
    symbol = "PHH"
    
    # Build prediction model
    model_result = engine.build_prediction_model(symbol)
    print("Model Results:", model_result)
    
    # Generate trading signals
    signals = engine.generate_trading_signals(symbol)
    print("Trading Signals:", signals)
    
    # Analyze lead-lag relationships
    lead_lag = engine.analyze_lead_lag_relationships(symbol)
    print("Lead-Lag Analysis:", lead_lag)