import os
import praw  # Reddit API
import tweepy  # Twitter API
import requests
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging
from dotenv import load_dotenv
from target_sources import TARGET_SUBS, TARGET_X_HANDLES, get_x_query

class SocialDataFetcher:
    def __init__(self, db_path="stock_data.db"):
        load_dotenv()
        self.db_path = db_path
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.init_social_database()
        self.use_mock_data = False
        
        # Initialize APIs
        self.reddit = None
        self.twitter_client = None  # v2 client
        self.setup_apis()
        
        # Use targeted sources instead of hardcoded lists
        self.target_stocks = ['PHH', 'OST', 'GME', 'AMC', 'BBBY', 'AAPL', 'TSLA']
        self.subreddits = TARGET_SUBS
        self.x_handles = TARGET_X_HANDLES
        
    def setup_apis(self):
        """Setup Reddit and Twitter v2 API connections"""
        reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        reddit_user_agent = os.getenv("REDDIT_USER_AGENT", "CrashGuardAI/1.0")

        twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN")

        # Reddit setup
        if reddit_client_id and reddit_client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    user_agent=reddit_user_agent
                )
                print("✅ Reddit API connected")
            except Exception as e:
                print(f"⚠️ Reddit API setup failed: {e}")
                print("   Check credentials at https://www.reddit.com/prefs/apps")
                self.use_mock_data = True
        else:
            print("ℹ️ Reddit credentials missing; using mock Reddit data")
            self.use_mock_data = True

        # Twitter v2 setup (uses Bearer token only)
        if twitter_bearer:
            try:
                self.twitter_client = tweepy.Client(bearer_token=twitter_bearer, wait_on_rate_limit=True)
                print("✅ Twitter v2 API connected")
            except Exception as e:
                print(f"⚠️ Twitter API setup failed: {e}")
                print("   Check credentials at https://developer.twitter.com")
                self.use_mock_data = True
        else:
            print("ℹ️ Twitter Bearer token missing; using mock Twitter data")
            self.use_mock_data = True
    
    def init_social_database(self):
        """Initialize database tables for social data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Social posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                symbol TEXT NOT NULL,
                post_id TEXT UNIQUE,
                author TEXT,
                title TEXT,
                content TEXT,
                score INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                created_utc TEXT,
                url TEXT,
                sentiment_score REAL,
                sentiment_label TEXT,
                mention_count INTEGER DEFAULT 1,
                timestamp TEXT
            )
        """)
        
        # Social hype metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_hype_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                platform TEXT NOT NULL,
                mention_volume INTEGER DEFAULT 0,
                avg_sentiment REAL DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                unique_authors INTEGER DEFAULT 0,
                hype_score REAL DEFAULT 0,
                timestamp TEXT,
                UNIQUE(symbol, date, platform)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Social database tables initialized")
    
    def extract_stock_mentions(self, text):
        """Extract stock ticker mentions from text"""
        if not text:
            return []
        
        # Pattern for $SYMBOL or SYMBOL mentions
        pattern = r'(?:\$|^|\s)([A-Z]{2,5})(?=\s|$|[^\w])'
        matches = re.findall(pattern, text.upper())
        
        # Filter for our target stocks only
        relevant_mentions = [match for match in matches if match in self.target_stocks]
        return list(set(relevant_mentions))  # Remove duplicates
    
    def analyze_post_sentiment(self, title, content=""):
        """Analyze sentiment of a social media post"""
        text = f"{title} {content}".strip()
        if not text:
            return {'score': 0, 'label': 'neutral'}
        
        scores = self.sentiment_analyzer.polarity_scores(text)
        compound = scores['compound']
        
        if compound >= 0.05:
            label = 'positive'
        elif compound <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'
            
        return {'score': compound, 'label': label}
    
    def fetch_reddit_posts(self, symbol, hours_back=24, limit=100):
        """Fetch Reddit posts mentioning a stock symbol"""
        if self.use_mock_data or not self.reddit:
            return self._generate_mock_reddit_data(symbol, hours_back)
        
        posts_data = []
        search_query = f"${symbol} OR {symbol}"
        
        try:
            for subreddit_name in self.subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # Search recent posts
                    for submission in subreddit.search(search_query, sort='new', time_filter='day', limit=limit//len(self.subreddits)):
                        # Check if post is within our time window
                        post_time = datetime.fromtimestamp(submission.created_utc)
                        if post_time < datetime.now() - timedelta(hours=hours_back):
                            continue
                        
                        # Extract mentions
                        mentions = self.extract_stock_mentions(f"{submission.title} {submission.selftext}")
                        if symbol not in mentions:
                            continue
                        
                        # Analyze sentiment
                        sentiment = self.analyze_post_sentiment(submission.title, submission.selftext)
                        
                        post_data = {
                            'platform': 'reddit',
                            'symbol': symbol,
                            'post_id': submission.id,
                            'author': str(submission.author) if submission.author else 'deleted',
                            'title': submission.title,
                            'content': submission.selftext[:500],  # Limit content length
                            'score': submission.score,
                            'comments_count': submission.num_comments,
                            'created_utc': post_time.isoformat(),
                            'url': f"https://reddit.com{submission.permalink}",
                            'sentiment_score': sentiment['score'],
                            'sentiment_label': sentiment['label'],
                            'mention_count': mentions.count(symbol),
                            'timestamp': datetime.now().isoformat()
                        }
                        posts_data.append(post_data)
                        
                except Exception as e:
                    print(f"Error fetching from r/{subreddit_name}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Reddit API error: {e}")
            self.use_mock_data = True
            return self._generate_mock_reddit_data(symbol, hours_back)
        
        return posts_data
    
    def fetch_twitter_posts(self, symbol, hours_back=24, limit=100):
        """Fetch Twitter v2 posts mentioning a stock symbol from target accounts"""
        if self.use_mock_data or not self.twitter_client:
            return self._generate_mock_twitter_data(symbol, hours_back)
        
        posts_data = []
        query = get_x_query(symbol, self.x_handles)
        
        try:
            # v2 API search with pagination
            tweets = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=min(limit, 100),
                tweet_fields=['public_metrics', 'created_at', 'author_id'],
                expansions=['author_id'],
                user_fields=['username']
            )
            
            if tweets and tweets.data:
                # Get user data
                user_map = {}
                if tweets.includes and tweets.includes.get('users'):
                    for user in tweets.includes['users']:
                        user_map[user.id] = user.username
                
                for tweet in tweets.data:
                    post_time = tweet.created_at
                    if post_time < datetime.now(post_time.tzinfo) - timedelta(hours=hours_back):
                        continue
                    
                    # Analyze sentiment
                    sentiment = self.analyze_post_sentiment(tweet.text)
                    
                    username = user_map.get(tweet.author_id, "unknown")
                    metrics = tweet.public_metrics or {}
                    
                    post_data = {
                        'platform': 'twitter',
                        'symbol': symbol,
                        'post_id': str(tweet.id),
                        'author': username,
                        'title': tweet.text[:100] + '...' if len(tweet.text) > 100 else tweet.text,
                        'content': tweet.text,
                        'score': metrics.get('like_count', 0) + metrics.get('retweet_count', 0),
                        'comments_count': metrics.get('reply_count', 0),
                        'created_utc': post_time.isoformat(),
                        'url': f"https://twitter.com/{username}/status/{tweet.id}",
                        'sentiment_score': sentiment['score'],
                        'sentiment_label': sentiment['label'],
                        'mention_count': 1,
                        'timestamp': datetime.now().isoformat()
                    }
                    posts_data.append(post_data)
                    
        except Exception as e:
            print(f"Twitter v2 API error: {e}")
            self.use_mock_data = True
            return self._generate_mock_twitter_data(symbol, hours_back)
        
        return posts_data
    
    def _generate_mock_reddit_data(self, symbol, hours_back):
        """Generate mock Reddit data for testing"""
        mock_posts = []
        
        # Sample realistic Reddit posts
        sample_posts = [
            {"title": f"${symbol} DD - This stock is undervalued!", "sentiment": 0.6, "score": 45},
            {"title": f"Anyone else buying {symbol} calls?", "sentiment": 0.3, "score": 12},
            {"title": f"{symbol} earnings coming up, thoughts?", "sentiment": 0.1, "score": 8},
            {"title": f"${symbol} to the moon! 🚀🚀🚀", "sentiment": 0.8, "score": 123},
            {"title": f"Why I'm shorting {symbol}", "sentiment": -0.4, "score": 23},
        ]
        
        for i, post in enumerate(sample_posts):
            mock_posts.append({
                'platform': 'reddit',
                'symbol': symbol,
                'post_id': f"mock_reddit_{symbol}_{i}",
                'author': f"user_{i}",
                'title': post['title'],
                'content': f"Mock content for {symbol} analysis...",
                'score': post['score'],
                'comments_count': post['score'] // 3,
                'created_utc': (datetime.now() - timedelta(hours=i)).isoformat(),
                'url': f"https://reddit.com/mock/{i}",
                'sentiment_score': post['sentiment'],
                'sentiment_label': 'positive' if post['sentiment'] > 0.1 else 'negative' if post['sentiment'] < -0.1 else 'neutral',
                'mention_count': 1,
                'timestamp': datetime.now().isoformat()
            })
        
        return mock_posts
    
    def _generate_mock_twitter_data(self, symbol, hours_back):
        """Generate mock Twitter data for testing"""
        mock_tweets = []
        
        sample_tweets = [
            {"text": f"Just bought more ${symbol}! Love this stock 📈", "sentiment": 0.5, "score": 15},
            {"text": f"{symbol} looking weak today, might sell", "sentiment": -0.3, "score": 3},
            {"text": f"Technical analysis on ${symbol} shows bullish pattern", "sentiment": 0.4, "score": 8},
            {"text": f"${symbol} earnings beat expectations! 🚀", "sentiment": 0.7, "score": 42},
        ]
        
        for i, tweet in enumerate(sample_tweets):
            mock_tweets.append({
                'platform': 'twitter',
                'symbol': symbol,
                'post_id': f"mock_twitter_{symbol}_{i}",
                'author': f"trader_{i}",
                'title': tweet['text'][:50] + '...',
                'content': tweet['text'],
                'score': tweet['score'],
                'comments_count': tweet['score'] // 5,
                'created_utc': (datetime.now() - timedelta(hours=i*2)).isoformat(),
                'url': f"https://twitter.com/mock/{i}",
                'sentiment_score': tweet['sentiment'],
                'sentiment_label': 'positive' if tweet['sentiment'] > 0.1 else 'negative' if tweet['sentiment'] < -0.1 else 'neutral',
                'mention_count': 1,
                'timestamp': datetime.now().isoformat()
            })
        
        return mock_tweets
    
    def save_social_posts(self, posts_data):
        """Save social posts to database"""
        if not posts_data:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for post in posts_data:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO social_posts 
                    (platform, symbol, post_id, author, title, content, score, 
                     comments_count, created_utc, url, sentiment_score, 
                     sentiment_label, mention_count, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    post['platform'], post['symbol'], post['post_id'], 
                    post['author'], post['title'], post['content'], post['score'],
                    post['comments_count'], post['created_utc'], post['url'],
                    post['sentiment_score'], post['sentiment_label'], 
                    post['mention_count'], post['timestamp']
                ))
            except Exception as e:
                print(f"Error saving post {post['post_id']}: {e}")
        
        conn.commit()
        conn.close()
    
    def fetch_all_social_data(self, symbol, hours_back=24):
        """Fetch social data from all platforms for a symbol"""
        print(f"📱 Fetching social data for ${symbol}...")
        
        all_posts = []
        
        # Fetch Reddit posts
        reddit_posts = self.fetch_reddit_posts(symbol, hours_back)
        all_posts.extend(reddit_posts)
        print(f"   Found {len(reddit_posts)} Reddit posts")
        
        # Fetch Twitter posts
        twitter_posts = self.fetch_twitter_posts(symbol, hours_back)
        all_posts.extend(twitter_posts)
        print(f"   Found {len(twitter_posts)} Twitter posts")
        
        # Save to database
        self.save_social_posts(all_posts)
        
        return all_posts
    
    def update_all_social_data(self, hours_back=24):
        """Update social data for all target stocks"""
        print("🔄 Updating social media data...")
        
        for symbol in self.target_stocks:
            try:
                self.fetch_all_social_data(symbol, hours_back)
                time.sleep(2)  # Be nice to APIs
            except Exception as e:
                print(f"Error updating {symbol}: {e}")
        
        print("✅ Social data update complete!")

# Usage example
if __name__ == "__main__":
    fetcher = SocialDataFetcher()
    
    # Test with a single stock
    posts = fetcher.fetch_all_social_data("PHH", hours_back=48)
    print(f"Fetched {len(posts)} posts for PHH")
    
    # Update all stocks
    # fetcher.update_all_social_data()