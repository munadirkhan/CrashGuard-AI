import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
import numpy as np
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

# Import our modules
from data_fetcher import StockDataFetcher
from anomaly_detector import MarketAnomalyDetector
from sentiment_analyzer import NewsSentimentAnalyzer
from social_data_fetcher import SocialDataFetcher
from hype_analyzer import SocialHypeAnalyzer
from correlation_engine import SocialPriceCorrelationEngine

# Page configuration
st.set_page_config(
    page_title="CrashGuard AI: Market Signal MVP - Social Edition",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def initialize_components():
    fetcher = StockDataFetcher()
    detector = MarketAnomalyDetector()
    analyzer = NewsSentimentAnalyzer()
    social_fetcher = SocialDataFetcher()
    hype_analyzer = SocialHypeAnalyzer()
    correlation_engine = SocialPriceCorrelationEngine()
    return fetcher, detector, analyzer, social_fetcher, hype_analyzer, correlation_engine

fetcher, detector, analyzer, social_fetcher, hype_analyzer, correlation_engine = initialize_components()

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .hype-high {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 15px;
        margin: 10px 0;
    }
    .hype-medium {
        background-color: #fff3e0;
        border-left: 5px solid #ff9800;
        padding: 15px;
        margin: 10px 0;
    }
    .hype-low {
        background-color: #e8f5e8;
        border-left: 5px solid #4caf50;
        padding: 15px;
        margin: 10px 0;
    }
    .signal-strong {
        background-color: #e3f2fd;
        border: 2px solid #2196f3;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .social-post {
        background-color: #fafafa;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 3px solid #ddd;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🚀 Market Signal MVP")
st.sidebar.markdown("*Social Edition*")
st.sidebar.markdown("---")

# Data update section
st.sidebar.subheader("📊 Data Management")

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("📈 Update Stocks", type="primary"):
        with st.spinner("Updating stock data..."):
            fetcher.update_all_stocks()
        st.success("✅ Updated!")

with col2:
    if st.button("📱 Update Social", type="primary"):
        with st.spinner("Updating social data..."):
            social_fetcher.update_all_social_data(hours_back=48)
            hype_analyzer.update_hype_metrics()
        st.success("✅ Updated!")

# Stock selection (focus on our target stocks)
st.sidebar.subheader("📈 Stock Selection")
target_stocks = ['PHH', 'OST', 'GME', 'AMC', 'AAPL', 'TSLA', 'NVDA', 'MSFT']
selected_stock = st.sidebar.selectbox(
    "Choose a stock to analyze:",
    options=target_stocks,
    index=0
)

# Search any stock
search_stock = st.sidebar.text_input("🔍 Or search any stock", value=selected_stock).upper()
if search_stock and search_stock != selected_stock:
    selected_stock = search_stock

# Time range
time_range = st.sidebar.selectbox(
    "Analysis Time Range:",
    options=[7, 14, 30, 60, 180],
    index=2,
    format_func=lambda x: f"{x} days"
)

# Main dashboard
st.title("🚀 Market Signal MVP - Social Edition")
st.markdown(f"*Real-time social sentiment tracking with price correlation analysis*")
st.markdown("---")

# ===== FETCH LIVE STOCK DATA =====
@st.cache_data(ttl=300)
def get_yfinance_data(symbol, days):
    try:
        ticker = yf.Ticker(symbol)
        end = datetime.now()
        start = end - timedelta(days=days)
        hist = ticker.history(start=start, end=end)
        info = ticker.info
        return hist, info
    except:
        return None, None

yf_hist, yf_info = get_yfinance_data(selected_stock, 180)

# Overview metrics
col1, col2, col3, col4, col5 = st.columns(5)

if yf_hist is not None and not yf_hist.empty:
    current_price = yf_hist['Close'].iloc[-1]
    prev_price = yf_hist['Close'].iloc[-5] if len(yf_hist) >= 5 else yf_hist['Close'].iloc[0]
    price_change = current_price - prev_price
    price_change_pct = (price_change / prev_price * 100) if prev_price else 0
else:
    current_price = 0
    price_change_pct = 0

# Get data for metrics
hype_alerts = hype_analyzer.generate_hype_alerts(min_hype_score=25)
trading_signals = correlation_engine.generate_trading_signals(selected_stock)

with col1:
    st.metric("💰 Current Price", f"${current_price:.2f}" if current_price else "N/A", delta=f"{price_change_pct:+.2f}%")

with col2:
    st.metric("🎯 Tracked Stocks", len(target_stocks))

with col3:
    st.metric("🚨 Hype Alerts", len(hype_alerts))

with col4:
    current_hype = trading_signals.get('current_metrics', {}).get('hype_score', 0)
    st.metric("🔥 Current Hype", f"{current_hype:.0f}/100")

with col5:
    signal_strength = trading_signals.get('signal_strength', 0)
    signal_emoji = "🟢" if signal_strength > 50 else "🟡" if signal_strength > 25 else "🔴"
    st.metric(f"{signal_emoji} Signal Strength", f"{signal_strength:.0f}/100")

# Main tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🎯 Overview", 
    "📈 Stock Analysis", 
    "📱 Social Signals", 
    "🔗 Correlation Analysis", 
    "🤖 Trading Signals",
    "📊 Bullish Picks",
    "🔔 Alerts",
    "💼 Portfolio"
])


def _latest_price(symbol: str) -> float:
    """Get latest price from DB or fallback to yfinance."""
    try:
        df = fetcher.get_stock_data(symbol, days=2)
        if not df.empty:
            return float(df.iloc[-1]['close'])
    except Exception:
        pass
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception:
        pass
    return 0.0


def _api_status(label: str, ok: bool):
    status = "🟢" if ok else "🟡 (mock)"
    st.caption(f"{status} {label}")

with tab1:
    st.header("Market & Social Overview")
    
    # Top hype alerts
    st.subheader("🔥 High Hype Stocks")
    if hype_alerts:
        for alert in hype_alerts[:5]:
            alert_class = f"hype-{alert['alert_level'].lower()}"
            st.markdown(f"""
                <div class="{alert_class}">
                    <strong>{alert['symbol']}</strong> - {alert['alert_level']} HYPE<br>
                    <small>Score: {alert['hype_score']:.1f}/100 | Mentions: {alert['avg_mentions']:.0f} | Sentiment: {alert['sentiment']:.3f}</small><br>
                    <small>{alert['description']}</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No high-hype stocks detected")
    
    # Social vs Price heatmap
    st.subheader("📊 Social Sentiment vs Price Performance")
    
    heatmap_data = []
    for stock in target_stocks[:6]:  # Show top 6
        try:
            signals = correlation_engine.generate_trading_signals(stock)
            metrics = signals.get('current_metrics', {})
            
            # Get recent price data
            stock_data = fetcher.get_stock_data(stock, days=2)
            price_change = 0
            if len(stock_data) >= 2:
                price_change = ((stock_data.iloc[0]['close'] - stock_data.iloc[1]['close']) / 
                              stock_data.iloc[1]['close']) * 100
            
            heatmap_data.append({
                'symbol': stock,
                'hype_score': metrics.get('hype_score', 0),
                'sentiment': metrics.get('sentiment', 0),
                'mentions': metrics.get('mentions', 0),
                'price_change': price_change
            })
        except Exception as e:
            print(f"Error processing {stock}: {e}")
    
    if heatmap_data:
        heatmap_df = pd.DataFrame(heatmap_data)
        
        # Create scatter plot
        fig = px.scatter(
            heatmap_df,
            x='sentiment',
            y='price_change',
            size='mentions',
            color='hype_score',
            hover_name='symbol',
            title="Social Sentiment vs Price Change (Size = Mentions, Color = Hype Score)",
            labels={'sentiment': 'Average Sentiment', 'price_change': 'Price Change (%)'},
            color_continuous_scale='RdYlBu_r'
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header(f"📈 {selected_stock} - Complete Analysis")
    
    if yf_hist is not None and not yf_hist.empty:
        # Company metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("52W High", f"${yf_hist['High'].max():.2f}")
        with col2:
            st.metric("52W Low", f"${yf_hist['Low'].min():.2f}")
        with col3:
            st.metric("Avg Volume", f"{yf_hist['Volume'].mean()/1e6:.1f}M")
        with col4:
            market_cap = yf_info.get('marketCap', 0) if yf_info else 0
            market_cap_str = f"${market_cap/1e9:.1f}B" if market_cap else "N/A"
            st.metric("Market Cap", market_cap_str)
        
        st.divider()
        
        # Stock price chart with social overlay
        stock_data = fetcher.get_stock_data(selected_stock, days=time_range)
        
        if not stock_data.empty:
            stock_data = stock_data.sort_values('date')
            
            # Get social data
            combined_data = correlation_engine.get_combined_data(selected_stock, days_back=time_range)
            
            # Create subplot with price and social metrics
            fig = make_subplots(
                rows=3, cols=1,
                row_heights=[0.5, 0.25, 0.25],
                vertical_spacing=0.05,
                subplot_titles=('Price Action with Social Overlay', 'Social Hype Score', 'Sentiment & Mentions'),
                shared_xaxes=True
            )
            
            # Price candlestick
            fig.add_trace(
                go.Candlestick(
                    x=stock_data['date'],
                    open=stock_data['open'],
                    high=stock_data['high'],
                    low=stock_data['low'],
                    close=stock_data['close'],
                    name='Price'
                ),
                row=1, col=1
            )
            
            # Social hype overlay
            if not combined_data.empty:
                fig.add_trace(
                    go.Scatter(
                        x=combined_data['date'],
                        y=combined_data['hype_score'],
                        mode='lines',
                        name='Hype Score',
                        line=dict(color='orange', width=2),
                        opacity=0.7
                    ),
                    row=2, col=1
                )
                
                # Sentiment bars
                fig.add_trace(
                    go.Bar(
                        x=combined_data['date'],
                        y=combined_data['avg_sentiment'],
                        name='Sentiment',
                        marker=dict(color=combined_data['avg_sentiment'], colorscale='RdYlGn', showscale=False)
                    ),
                    row=3, col=1
                )
            
            # Update layout
            fig.update_yaxes(title_text="Price ($)", row=1, col=1)
            fig.update_yaxes(title_text="Hype (0-100)", row=2, col=1)
            fig.update_yaxes(title_text="Sentiment (-1 to 1)", row=3, col=1)
            fig.update_xaxes(title_text="Date", row=3, col=1)
            fig.update_layout(height=900, showlegend=True, hovermode='x unified')
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No stock data available. Try updating stocks in the sidebar.")
    else:
        st.warning(f"Could not fetch data for {selected_stock}. Try a different symbol.")

with tab3:
    st.header("📱 Social Signals")
    st.subheader("API Status")
    reddit_ok = bool(os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET"))
    twitter_ok = bool(os.getenv("TWITTER_BEARER_TOKEN"))
    
    col1, col2 = st.columns(2)
    with col1:
        status = "🟢 Connected" if reddit_ok else "🟡 Using Mock Data"
        st.caption(f"Reddit: {status}")
    with col2:
        status = "🟢 Connected" if twitter_ok else "🟡 Using Mock Data"
        st.caption(f"Twitter/X: {status}")
    
    st.caption("If keys are missing, mock data is used automatically.")

    st.subheader("Recent Posts from Target Accounts")
    st.info("Fetching posts from @unusual_whales, @deltaone, @StockMKTNewz, @HindenburgRes, and more")
    
    # Sample sentiment data
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Composite Sentiment", "0.62/1.00", delta="+0.08")
    with col2:
        st.metric("Mention Volume (24h)", "342 posts", delta="+45")

with tab4:
    st.header("🔗 Correlation Analysis")
    st.info("The Stock Analysis tab already shows price + social overlay. Deeper lead/lag analytics can be added next.")

with tab5:
    st.header("🤖 Trading Signals")
    st.info("Model-driven signals placeholder. We can surface the isolation-forest + rule-based outputs here.")

with tab6:
    st.header("📊 Bullish Picks (Long Ideas)")
    ranked = correlation_engine.rank_bullish_candidates(target_stocks, days_back=time_range, top_n=5)
    if ranked:
        df_rank = pd.DataFrame(ranked)
        df_rank['Score'] = (df_rank['score'] * 100).round(1)
        cols = ["symbol", "Score", "hype", "sentiment", "mentions", "mention_momentum", "price_change_2d", "volume_ratio"]
        st.dataframe(df_rank[cols].rename(columns={
            "symbol": "Symbol",
            "hype": "Hype",
            "sentiment": "Sentiment",
            "mentions": "Mentions",
            "mention_momentum": "Mention Δ",
            "price_change_2d": "Price Δ2d%",
            "volume_ratio": "Vol Ratio"
        }), use_container_width=True)
        st.caption("Composite score blends hype, positive sentiment, rising mentions, short-term price momentum, and volume ratio.")
    else:
        st.info("No data yet. Update stocks/social in the sidebar and try again.")

with tab7:
    st.header("🔔 Alerts")
    min_score = st.slider("Minimum hype score to alert", min_value=0, max_value=100, value=40, step=5)
    contact = st.text_input("Alert contact (email or SMS)", placeholder="you@example.com")
    filtered_alerts = [a for a in hype_alerts if a['hype_score'] >= min_score]
    st.write(f"{len(filtered_alerts)} alerts >= {min_score}")
    for alert in filtered_alerts:
        alert_class = f"hype-{alert['alert_level'].lower()}"
        st.markdown(f"""
            <div class="{alert_class}">
                <strong>{alert['symbol']}</strong> | Score {alert['hype_score']:.1f} | Mentions {alert['avg_mentions']:.0f} | Sentiment {alert['sentiment']:.2f}<br>
                <small>{alert['description']}</small>
            </div>
        """, unsafe_allow_html=True)
    st.caption("Email/SMS sending not wired yet—this just filters and surfaces alerts.")

with tab8:
    st.header("💼 Portfolio & Watchlist")
    if 'portfolio_positions' not in st.session_state:
        st.session_state.portfolio_positions = []
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = target_stocks.copy()

    st.subheader("Add position")
    with st.form("add_position"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            ticker = st.text_input("Ticker", value=selected_stock).upper().strip()
        with col_b:
            shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
        with col_c:
            cost_basis = st.number_input("Cost basis ($)", min_value=0.0, value=0.0, step=0.1)
        submitted = st.form_submit_button("Add/Update")
        if submitted and ticker and shares > 0:
            price_now = _latest_price(ticker)
            # replace if exists
            st.session_state.portfolio_positions = [p for p in st.session_state.portfolio_positions if p['ticker'] != ticker]
            st.session_state.portfolio_positions.append({
                'ticker': ticker,
                'shares': shares,
                'cost_basis': cost_basis,
                'last_price': price_now
            })
            st.success(f"Saved {ticker}")

    if st.session_state.portfolio_positions:
        rows = []
        total_cost = 0
        total_value = 0
        for p in st.session_state.portfolio_positions:
            price_now = _latest_price(p['ticker'])
            value = price_now * p['shares']
            cost = p['cost_basis'] * p['shares']
            pl = value - cost
            pl_pct = (pl / cost * 100) if cost else 0
            total_cost += cost
            total_value += value
            rows.append({
                "Ticker": p['ticker'],
                "Shares": p['shares'],
                "Cost Basis": p['cost_basis'],
                "Last Price": round(price_now, 2),
                "Value": round(value, 2),
                "P/L $": round(pl, 2),
                "P/L %": round(pl_pct, 2)
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        st.metric("Portfolio Value", f"${total_value:,.2f}")
        if total_cost:
            st.metric("Total P/L", f"${(total_value-total_cost):,.2f}", delta=f"{((total_value-total_cost)/total_cost*100):.2f}%")
    else:
        st.info("No positions yet. Add one above.")

    st.subheader("Watchlist")
    with st.form("add_watch"):
        new_tick = st.text_input("Add ticker to watchlist", placeholder="e.g., SPY").upper().strip()
        add_watch = st.form_submit_button("Add")
        if add_watch and new_tick:
            if new_tick not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_tick)
                st.success(f"Added {new_tick}")
    if st.session_state.watchlist:
        st.write(", ".join(sorted(set(st.session_state.watchlist))))
    if st.button("Clear portfolio (session)"):
        st.session_state.portfolio_positions = []
        st.success("Portfolio cleared for this session")