import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
import yfinance as yf
from correlation_engine import SocialPriceCorrelationEngine
from data_fetcher import StockDataFetcher
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

class SocialTradingBacktester:
    def __init__(self, db_path="stock_data.db", initial_capital=10000):
        self.db_path = db_path
        self.initial_capital = initial_capital
        self.correlation_engine = SocialPriceCorrelationEngine(db_path)
        self.fetcher = StockDataFetcher(db_path)
        
    def generate_historical_social_data(self, symbol, start_date, end_date):
        """Generate realistic historical social data for backtesting"""
        # This simulates social data since we don't have historical Reddit/Twitter data
        # In production, you'd use archived social media data or real historical data
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Get actual price data to inform social sentiment simulation
        ticker = yf.Ticker(symbol)
        price_data = ticker.history(start=start_date, end=end_date)
        
        if price_data.empty:
            return pd.DataFrame()
        
        social_data = []
        
        for date in date_range:
            if date.strftime('%Y-%m-%d') not in price_data.index.strftime('%Y-%m-%d'):
                continue
                
            price_row = price_data.loc[price_data.index.date == date.date()]
            if price_row.empty:
                continue
                
            price_row = price_row.iloc[0]
            
            # Calculate price change to inform sentiment
            if len(price_data.loc[:date]) > 1:
                prev_close = price_data.loc[:date].iloc[-2]['Close']
                price_change = (price_row['Close'] - prev_close) / prev_close
            else:
                price_change = 0
            
            # Simulate social metrics based on price action and volatility
            base_mentions = np.random.poisson(20)  # Base daily mentions
            
            # Volume spike increases mentions
            if price_row['Volume'] > price_data['Volume'].rolling(20).mean().loc[date]:
                volume_multiplier = 1.5
            else:
                volume_multiplier = 1.0
            
            # Large price moves increase mentions
            if abs(price_change) > 0.05:  # 5% move
                price_multiplier = 1 + abs(price_change) * 5
            else:
                price_multiplier = 1.0
            
            mention_volume = int(base_mentions * volume_multiplier * price_multiplier)
            
            # Sentiment correlates with price direction but with noise
            base_sentiment = price_change * 2  # Scale price change to sentiment
            sentiment_noise = np.random.normal(0, 0.1)  # Add noise
            avg_sentiment = np.clip(base_sentiment + sentiment_noise, -1, 1)
            
            # Hype score based on mentions and sentiment
            hype_score = min(100, (mention_volume / 20) * 10 + abs(avg_sentiment) * 20 + np.random.normal(0, 5))
            hype_score = max(0, hype_score)
            
            social_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'symbol': symbol,
                'mention_volume': mention_volume,
                'avg_sentiment': avg_sentiment,
                'hype_score': hype_score,
                'unique_authors': int(mention_volume * 0.7),  # Estimate unique authors
                'platform': 'combined'
            })
        
        return pd.DataFrame(social_data)
    
    def populate_backtest_data(self, symbol, start_date, end_date):
        """Populate database with historical data for backtesting"""
        print(f"📊 Populating backtest data for {symbol} from {start_date} to {end_date}")
        
        # Get stock data
        ticker = yf.Ticker(symbol)
        price_data = ticker.history(start=start_date, end=end_date)
        
        if price_data.empty:
            print(f"❌ No price data found for {symbol}")
            return False
        
        # Save stock data
        conn = sqlite3.connect(self.db_path)
        
        for date, row in price_data.iterrows():
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO stock_data 
                    (symbol, date, open, high, low, close, volume, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, date.strftime('%Y-%m-%d'),
                    row['Open'], row['High'], row['Low'], row['Close'],
                    int(row['Volume']), datetime.now().isoformat()
                ))
            except Exception as e:
                print(f"Error saving price data: {e}")
        
        # Generate and save social data
        social_data = self.generate_historical_social_data(symbol, start_date, end_date)
        
        for _, row in social_data.iterrows():
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO social_hype_metrics 
                    (symbol, date, platform, mention_volume, avg_sentiment, 
                     unique_authors, hype_score, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['symbol'], row['date'], 'combined',
                    row['mention_volume'], row['avg_sentiment'],
                    row['unique_authors'], row['hype_score'],
                    datetime.now().isoformat()
                ))
            except Exception as e:
                print(f"Error saving social data: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Populated {len(price_data)} price records and {len(social_data)} social records")
        return True
    
    def run_social_signal_backtest(self, symbol, start_date, end_date, 
                                 min_hype_threshold=40, min_confidence=0.5):
        """Run backtest using social signals for trading decisions"""
        
        # Ensure data is available
        if not self.populate_backtest_data(symbol, start_date, end_date):
            return {'error': 'Failed to populate backtest data'}
        
        # Get combined data
        combined_data = self.correlation_engine.get_combined_data(
            symbol, 
            days_back=(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
        )
        
        if combined_data.empty:
            return {'error': 'No combined data available for backtesting'}
        
        combined_data = combined_data.sort_values('date')
        
        # Initialize portfolio
        portfolio = {
            'cash': self.initial_capital,
            'shares': 0,
            'total_value': self.initial_capital,
            'trades': [],
            'daily_values': []
        }
        
        # Train model on first 60% of data, test on remaining 40%
        train_split = int(len(combined_data) * 0.6)
        
        # Build prediction model
        model_result = self.correlation_engine.build_prediction_model(symbol)
        if 'error' in model_result:
            return {'error': f'Model building failed: {model_result["error"]}'}
        
        print(f"🤖 Model trained with R² = {model_result['r2_score']:.3f}")
        
        # Run backtest on test period
        test_data = combined_data.iloc[train_split:].copy()
        
        for i, (_, row) in enumerate(test_data.iterrows()):
            current_price = row['close']
            current_date = row['date']
            
            # Calculate current portfolio value
            portfolio_value = portfolio['cash'] + (portfolio['shares'] * current_price)
            portfolio['daily_values'].append({
                'date': current_date,
                'portfolio_value': portfolio_value,
                'stock_price': current_price,
                'cash': portfolio['cash'],
                'shares': portfolio['shares']
            })
            
            # Skip if we don't have enough historical data for prediction
            if i < 10:
                continue
            
            # Generate trading signal
            try:
                # Get current social metrics
                hype_score = row.get('hype_score', 0)
                sentiment = row.get('avg_sentiment', 0)
                mention_volume = row.get('mention_volume', 0)
                
                # Simple signal rules (you can enhance with ML prediction)
                signal = None
                confidence = 0
                
                # Rule 1: High hype with positive sentiment
                if hype_score > min_hype_threshold and sentiment > 0.2:
                    signal = 'BUY'
                    confidence = min(hype_score / 100 + abs(sentiment), 1.0)
                
                # Rule 2: High hype with negative sentiment (potential short)
                elif hype_score > min_hype_threshold and sentiment < -0.2:
                    signal = 'SELL'
                    confidence = min(hype_score / 100 + abs(sentiment), 1.0)
                
                # Rule 3: Very low hype after high hype (momentum reversal)
                elif i > 0 and hype_score < 10:
                    prev_hype = test_data.iloc[i-1].get('hype_score', 0)
                    if prev_hype > 50:
                        signal = 'SELL'
                        confidence = 0.6
                
                # Execute trade if confidence is high enough
                if signal and confidence >= min_confidence:
                    
                    if signal == 'BUY' and portfolio['shares'] == 0 and portfolio['cash'] > current_price:
                        # Buy maximum shares
                        shares_to_buy = int(portfolio['cash'] / current_price)
                        cost = shares_to_buy * current_price
                        
                        portfolio['shares'] += shares_to_buy
                        portfolio['cash'] -= cost
                        
                        portfolio['trades'].append({
                            'date': current_date,
                            'action': 'BUY',
                            'shares': shares_to_buy,
                            'price': current_price,
                            'cost': cost,
                            'hype_score': hype_score,
                            'sentiment': sentiment,
                            'confidence': confidence
                        })
                        
                        print(f"📈 BUY {shares_to_buy} shares at ${current_price:.2f} (Hype: {hype_score:.1f}, Sentiment: {sentiment:.3f})")
                    
                    elif signal == 'SELL' and portfolio['shares'] > 0:
                        # Sell all shares
                        revenue = portfolio['shares'] * current_price
                        shares_sold = portfolio['shares']
                        
                        portfolio['cash'] += revenue
                        portfolio['shares'] = 0
                        
                        portfolio['trades'].append({
                            'date': current_date,
                            'action': 'SELL',
                            'shares': shares_sold,
                            'price': current_price,
                            'revenue': revenue,
                            'hype_score': hype_score,
                            'sentiment': sentiment,
                            'confidence': confidence
                        })
                        
                        print(f"📉 SELL {shares_sold} shares at ${current_price:.2f} (Hype: {hype_score:.1f}, Sentiment: {sentiment:.3f})")
                
            except Exception as e:
                print(f"Error processing row {i}: {e}")
                continue
        
        # Calculate final portfolio value
        if test_data.empty:
            final_price = combined_data.iloc[-1]['close']
        else:
            final_price = test_data.iloc[-1]['close']
            
        final_value = portfolio['cash'] + (portfolio['shares'] * final_price)
        
        # Calculate performance metrics
        performance = self.calculate_performance_metrics(
            portfolio, symbol, start_date, end_date, test_data
        )
        
        return {
            'symbol': symbol,
            'period': f"{start_date} to {end_date}",
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': (final_value - self.initial_capital) / self.initial_capital,
            'total_trades': len(portfolio['trades']),
            'performance_metrics': performance,
            'trades': portfolio['trades'],
            'daily_values': portfolio['daily_values'],
            'model_performance': model_result
        }
    
    def calculate_performance_metrics(self, portfolio, symbol, start_date, end_date, test_data):
        """Calculate comprehensive performance metrics"""
        
        if not portfolio['daily_values']:
            return {}
        
        daily_df = pd.DataFrame(portfolio['daily_values'])
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        daily_df = daily_df.sort_values('date')
        
        # Calculate daily returns
        daily_df['portfolio_return'] = daily_df['portfolio_value'].pct_change()
        daily_df['stock_return'] = daily_df['stock_price'].pct_change()
        
        # Remove NaN values
        returns_df = daily_df.dropna()
        
        if returns_df.empty:
            return {}
        
        # Portfolio metrics
        total_return = (daily_df.iloc[-1]['portfolio_value'] - self.initial_capital) / self.initial_capital
        
        portfolio_returns = returns_df['portfolio_return']
        stock_returns = returns_df['stock_return']
        
        # Risk metrics
        portfolio_volatility = portfolio_returns.std() * np.sqrt(252)  # Annualized
        stock_volatility = stock_returns.std() * np.sqrt(252)
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = (portfolio_returns.mean() * 252) / (portfolio_volatility + 1e-8)
        
        # Maximum drawdown
        running_max = daily_df['portfolio_value'].expanding().max()
        drawdown = (daily_df['portfolio_value'] - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Win rate
        if portfolio['trades']:
            winning_trades = 0
            for i in range(1, len(portfolio['trades'])):
                if portfolio['trades'][i]['action'] == 'SELL':
                    buy_price = portfolio['trades'][i-1]['price']
                    sell_price = portfolio['trades'][i]['price']
                    if sell_price > buy_price:
                        winning_trades += 1
            
            total_trades = len([t for t in portfolio['trades'] if t['action'] == 'SELL'])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
        else:
            win_rate = 0
        
        return {
            'total_return_pct': total_return_pct,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(portfolio['trades']),
            'final_portfolio_value': portfolio['portfolio_value']
        }