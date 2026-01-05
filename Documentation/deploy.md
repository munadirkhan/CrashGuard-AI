# Deployment Guide - Market Signal MVP

## Quick Deploy to Streamlit Cloud (Recommended)

### Prerequisites
- GitHub account
- All code files in a GitHub repository

### Steps


2. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Market Signal MVP"
   git branch -M main
   git remote add origin https://github.com/yourusername/market-signal-mvp.git
   git push -u origin main
   ```

3. **Deploy to Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Connect your GitHub account
   - Select your repository and `app.py`
   - Click "Deploy"

4. **Set Environment Variables (Optional):**
   - In Streamlit Cloud dashboard, go to "Secrets"
   - Add NewsAPI key if you have one:
     ```toml
     NEWS_API_KEY = "your_api_key_here"
     ```

### Alternative: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Azure Deployment (Optional)

If you want to use Azure (since you mentioned familiarity):

### 1. Azure Container Instances

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Deploy:
```bash
# Build and push to Azure Container Registry
az acr build --registry myregistry --image market-signal:latest .

# Deploy to Container Instance
az container create \
  --resource-group myResourceGroup \
  --name market-signal \
  --image myregistry.azurecr.io/market-signal:latest \
  --ports 8501
```

### 2. Azure App Service

```bash
# Create App Service plan
az appservice plan create \
  --name market-signal-plan \
  --resource-group myResourceGroup \
  --sku B1 --is-linux

# Create web app
az webapp create \
  --resource-group myResourceGroup \
  --plan market-signal-plan \
  --name market-signal-app \
  --deployment-container-image-name python:3.9-slim
```

## Environment Variables

For production deployment, set these environment variables:

```bash
# Optional - NewsAPI key for real news data
NEWS_API_KEY=your_newsapi_key_here

# Database configuration
DATABASE_PATH=stock_data.db

# Update frequency (minutes)
UPDATE_FREQUENCY=60
```

## Performance Optimization

1. **Database Indexing:**
   ```sql
   CREATE INDEX idx_symbol_date ON stock_data(symbol, date);
   CREATE INDEX idx_news_symbol_date ON news_sentiment(symbol, date);
   ```

2. **Caching in Streamlit:**
   ```python
   @st.cache_data(ttl=300)  # Cache for 5 minutes
   def get_stock_data(symbol, days):
       return fetcher.get_stock_data(symbol, days)
   ```

3. **Async Data Updates:**
   - Consider using a separate script to update data periodically
   - Use GitHub Actions or Azure Functions for scheduled updates

## Monitoring & Debugging

1. **Add Logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   ```

2. **Health Check Endpoint:**
   ```python
   # Add to app.py
   @st.cache_data
   def health_check():
       return {"status": "healthy", "timestamp": datetime.now()}
   ```

3. **Error Handling:**
   ```python
   try:
       data = fetcher.update_all_stocks()
   except Exception as e:
       st.error(f"Failed to update data: {e}")
       logging.error(f"Data update failed: {e}")
   ```

## Cost Considerations

**Free Tiers:**
- Streamlit Cloud: Free for public repos
- NewsAPI: 1000 requests/month free
- Azure: $200 credit for students

**Optimizations:**
- Use caching to reduce API calls
- Implement data retention policies
- Consider using free financial APIs as alternatives

## Security Notes

1. **Never commit API keys to GitHub**
2. **Use Streamlit secrets management**
3. **Validate all user inputs**
4. **Implement rate limiting if needed**

## Backup Strategy

```python
# Add to data_fetcher.py
def backup_database(self):
    import shutil
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(self.db_path, f"backup_stock_data_{timestamp}.db")
```