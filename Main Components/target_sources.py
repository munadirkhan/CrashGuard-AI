"""
Targeted data sources for CrashGuard AI
High-signal Reddit subs and X accounts for pump-and-dump detection
"""

TARGET_SUBS = [
    "wallstreetbets", 
    "pennystocks", 
    "Shortsqueeze", 
    "SqueezePlay", 
    "stocks", 
    "investing", 
    "StockMarket", 
    "SecurityAnalysis",
    "ValueInvesting"
]

TARGET_X_HANDLES = [
    "unusual_whales", 
    "deltaone", 
    "StockMKTNewz", 
    "HindenburgRes", 
    "MrZackMorris", 
    "Stocktwits", 
    "CNBC", 
    "WSJMarkets"
]

def get_x_query(symbol: str, handles: list = None) -> str:
    """Generate X v2 query: ($SYMBOL) (from:handle1 OR from:handle2 ...)"""
    if handles is None:
        handles = TARGET_X_HANDLES
    
    from_filter = " OR ".join([f"from:{h}" for h in handles])
    query = f"(${symbol}) ({from_filter})"
    return query
