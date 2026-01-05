# Import necessary libraries
import yfinance as yf #Free API for stock data
import pandas as pd #Data manipulation and analysis
import numpy as np #Numerical operations
from datetime import datetime, timedelta #Date and time operations
import sqlite3 #Database operations
import os #Operating system operations

# Define the stock symbol and time period
symbol = "AAPL" #Stock symbol

#CLASS to fetch and store stock data from Yahoo Finance
class StockDataFetcher:
    def __init__(self, db_path="stock_data.db"):
        self.db_path = db_path
        self.init_database()

        #Popular Stocks for Demo
        self.watchlist = [
            "AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOG", "META", "NFLX", "INTC", "AMD"
        ]

    #Initialize the SQLite database - for persistence
    def init_database(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        #Create a table to store stock data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                timestamp TEXT,
                UNIQUE(symbol, date)
            )
        """)

        conn.commit()
        conn.close()

    #Fetch stock data from Yahoo Finance
    def fetch_stock_data(self, symbol, period ="1mo"):
        """Fetch stock data fora symbol from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period = period)
            
            if data.empty:
                print(f"No data found ofr {symbol}")
                return None
            
            #Clean and prepare data
            data = data.reset_index()
            data['Symbol'] = symbol
            data['Date'] = data['Date'].dt.strftime('%Y-%m-%d')
            data['Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            return data[['Symbol', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Timestamp']]
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    def save_to_database(self,data,symbol):
        """Save stock data to SQLite Databasae"""
        if data is None or data.empty:
            return
        
        conn = sqlite3.connect(self.db_path)

        for _, row in data.iterrows():
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO stock_data 
                    (symbol, date, open, high, low, close, volume, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['Symbol'], row['Date'], row['Open'], 
                    row['High'], row['Low'], row['Close'], 
                    row['Volume'], row['Timestamp']
                ))
            except Exception as e:
                print(f"Error inserting data for {symbol}: {e}")
        
        conn.commit()
        conn.close()
                
# This (gets) the info for said stock from SQL database and call its to frontend streamlit 
    def update_all_stocks(self):
        """Update all stocks in watchlist"""
        print("updating the stock data...")

        for symbol in self.watchlist:
            print(f"Fetching {symbol}...")
            data = self.fetch_stock_data(symbol)
            self.save_to_database(data, symbol)

        print("Data update complete!")

    def get_stock_data(self, symbol, days=30):
        """Get stock data from database"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT symbol, date, open, high, low, close, volume, timestamp
            FROM stock_data 
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(symbol, days))
        conn.close()
        
        return df.sort_values('date')

    def get_latest_prices(self):
        """Get latest prices for all stocks on NYSE, TSX"""
        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT symbol, close, volume, date
            FROM stock_data s1
            WHERE date = (
                SELECT MAX(date) 
                FROM stock_data s2 
                WHERE s2.symbol = s1.symbol
            )
            ORDER BY symbol
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df
    
    #Usage example
    if __name__ == "__main__":
        fetcher = StockDataFetcher()
        
        #Update all stocks
        fetcher.update_all_stocks()

        #Get data for a specific stock
        aapl_data = fetcher.get_stock_data("AAPL", days=30)
        print(aapl_data.head())

        #Get latest prices
        latest = fetcher.get_latest_prices()
        print(latest)



