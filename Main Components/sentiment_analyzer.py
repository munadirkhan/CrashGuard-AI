#Social media sentiment analysis - often precedes major price movements by hours or days.
#Sentiment analysis is the process of identifying and extracting subjective information from text.
#We will use the Twitter API to collect tweets and perform sentiment analysis.
import requests
import pandas as pd
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import sqlite3
import time

class NewsSentimentAnalyzer:
    def __init__(self, api_key=None, db_path="stock_data.db"):
        self.api_key = api_key  # NewsAPI key (get free at newsapi.org)
        self.db_path = db_path
        self.analyzer = SentimentIntensityAnalyzer()
        self.init_news_database()
        
        # Stock name mappings for better news search
        self.stock_names = {
            'AAPL': 'Apple',
            'TSLA': 'Tesla',
            'GOOGL': 'Google Alphabet',
            'AMZN': 'Amazon',
            'MSFT': 'Microsoft',
            'NVDA': 'Nvidia',
            'META': 'Meta Facebook',
            'NFLX': 'Netflix',
            'AMD': 'AMD',
            'GME': 'GameStop'
        }
    
    def init_news_database(self):
        """Initialize database for news sentiment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_sentiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                headline TEXT,
                description TEXT,
                url TEXT,
                sentiment_score REAL,
                sentiment_label TEXT,
                timestamp TEXT,
                UNIQUE(symbol, url)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def fetch_news(self, symbol, days=7):
        """Fetch news for a stock symbol"""
        if not self.api_key:
            return self._get_mock_news(symbol)  # Return mock data if no API key
        
        company_name = self.stock_names.get(symbol, symbol)
        
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': f'{company_name} OR {symbol}',
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d'),
            'sortBy': 'publishedAt',
            'language': 'en',
            'apiKey': self.api_key,
            'pageSize': 20
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'ok':
                return data['articles']
            else:
                print(f"Error fetching news: {data.get('message', 'Unknown error')}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching news for {symbol}: {e}")
            return []
    
    def _get_mock_news(self, symbol):
        """Generate mock news data for testing without API key"""
        mock_headlines = {
            'AAPL': [
                "Apple Reports Strong Q3 Earnings, iPhone Sales Surge",
                "Apple Stock Hits New All-Time High Amid AI Optimism",
                "Analysts Upgrade Apple Stock Target Price"
            ],
            'TSLA': [
                "Tesla Delivers Record Number of Vehicles in Q3",
                "Musk Announces New Tesla Gigafactory Plans",
                "Tesla Stock Volatile After Earnings Miss"
            ],
            'GOOGL': [
                "Google Parent Alphabet Beats Revenue Expectations",
                "Google AI Advancements Drive Stock Price Higher",
                "Regulatory Concerns Impact Google Stock Performance"
            ]
        }
        
        headlines = mock_headlines.get(symbol, [f"{symbol} shows strong market performance"])
        
        mock_articles = []
        for i, headline in enumerate(headlines):
            mock_articles.append({
                'title': headline,
                'description': f"Market analysis and news about {symbol} performance...",
                'url': f"https://example.com/news/{symbol.lower()}-{i}",
                'publishedAt': (datetime.now() - timedelta(days=i)).isoformat()
            })
        
        return mock_articles
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of text using VADER"""
        if not text:
            return {'score': 0, 'label': 'neutral'}
        
        scores = self.analyzer.polarity_scores(text)
        compound_score = scores['compound']
        
        # Classify sentiment
        if compound_score >= 0.05:
            label = 'positive'
        elif compound_score <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            'score': compound_score,
            'label': label,
            'detailed_scores': scores
        }
    
    def process_news_sentiment(self, symbol):
        """Process news and sentiment for a stock"""
        articles = self.fetch_news(symbol)
        
        if not articles:
            return []
        
        sentiment_data = []
        
        for article in articles:
            # Combine title and description for sentiment analysis
            text = f"{article.get('title', '')} {article.get('description', '')}"
            sentiment = self.analyze_sentiment(text)
            
            sentiment_item = {
                'symbol': symbol,
                'date': article.get('publishedAt', datetime.now().isoformat())[:10],
                'headline': article.get('title', ''),
                'description': article.get('description', ''),
                'url': article.get('url', ''),
                'sentiment_score': sentiment['score'],
                'sentiment_label': sentiment['label'],
                'timestamp': datetime.now().isoformat()
            }
            
            sentiment_data.append(sentiment_item)
        
        return sentiment_data
    
    def save_sentiment_to_db(self, sentiment_data):
        """Save sentiment data to database"""
        if not sentiment_data:
            return
        
        conn = sqlite3.connect(self.db_path)
        
        for item in sentiment_data:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO news_sentiment 
                    (symbol, date, headline, description, url, 
                     sentiment_score, sentiment_label, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['symbol'], item['date'], item['headline'],
                    item['description'], item['url'], item['sentiment_score'],
                    item['sentiment_label'], item['timestamp']
                ))
            except Exception as e:
                print(f"Error saving sentiment data: {e}")
        
        conn.commit()
        conn.close()
    
    def get_sentiment_summary(self, symbol, days=7):
        """Get sentiment summary for a stock"""
        conn = sqlite3.connect(self.db_path)
        
        date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        query = """
            SELECT sentiment_score, sentiment_label, headline, date
            FROM news_sentiment 
            WHERE symbol = ? AND date >= ?
            ORDER BY date DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(symbol, date_threshold))
        conn.close()
        
        if df.empty:
            return {
                'avg_sentiment': 0,
                'sentiment_trend': 'neutral',
                'article_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'recent_headlines': []
            }
        
        # Calculate statistics
        avg_sentiment = df['sentiment_score'].mean()
        
        # Count sentiment labels
        sentiment_counts = df['sentiment_label'].value_counts()
        
        # Determine trend
        if avg_sentiment > 0.1:
            trend = 'positive'
        elif avg_sentiment < -0.1:
            trend = 'negative'
        else:
            trend = 'neutral'
        
        return {
            'avg_sentiment': avg_sentiment,
            'sentiment_trend': trend,
            'article_count': len(df),
            'positive_count': sentiment_counts.get('positive', 0),
            'negative_count': sentiment_counts.get('negative', 0),
            'neutral_count': sentiment_counts.get('neutral', 0),
            'recent_headlines': df[['headline', 'sentiment_score', 'date']].head(5).to_dict('records')
        }
    
    def update_all_sentiment(self, stock_list):
        """Update sentiment for all stocks"""
        print("Updating news sentiment...")
        
        for symbol in stock_list:
            print(f"Processing sentiment for {symbol}...")
            sentiment_data = self.process_news_sentiment(symbol)
            self.save_sentiment_to_db(sentiment_data)
            time.sleep(1)  # Be nice to the API
        
        print("Sentiment update complete!")
    
    def get_market_sentiment_overview(self):
        """Get overall market sentiment"""
        conn = sqlite3.connect(self.db_path)
        
        # Get recent sentiment data
        date_threshold = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        query = """
            SELECT symbol, AVG(sentiment_score) as avg_sentiment,
                   COUNT(*) as article_count
            FROM news_sentiment 
            WHERE date >= ?
            GROUP BY symbol
            ORDER BY avg_sentiment DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(date_threshold,))
        conn.close()
        
        return df

# Usage example
if __name__ == "__main__":
    # Initialize with your NewsAPI key (get free at newsapi.org)
    analyzer = NewsSentimentAnalyzer(api_key=None)  # Will use mock data
    
    # Process sentiment for a stock
    sentiment_data = analyzer.process_news_sentiment("AAPL")
    analyzer.save_sentiment_to_db(sentiment_data)
    
    # Get sentiment summary
    summary = analyzer.get_sentiment_summary("AAPL")
    print("AAPL Sentiment Summary:", summary)
    
    # Get market overview
    market_sentiment = analyzer.get_market_sentiment_overview()
    print("Market Sentiment Overview:")
    print(market_sentiment)