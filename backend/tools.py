# Creates the tools that the agent will use during execution.

# Imports logging and environment variable importing components
from dotenv import load_dotenv
import logging
import json
from datetime import datetime
import hashlib

# Cache and TTL
import redis
from functools import wraps

# Imports the tool components 
import yfinance as yf
from langchain.tools import tool
from tavily import TavilyClient

# Environment variable loading and logger config
load_dotenv()
logger = logging.getLogger(__name__)

# === REDIS CACHE ===
try:
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True # str instead of bytes
    )
    redis_client.ping() # Tests conn
    logger.info("Redis cache connected successfully")
except Exception as e:
    logger.warning(f"Redis unavailable, falling back to no cache: {str(e)}")
    redis_client = None

# Redis cache decorator
def redis_cache(ttl: int):
    """Redis cache decorator with TTL."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if redis_client is None:
                return func(*args, **kwargs)
            cache_key = f"{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    logger.info(f"Cache HIT: {func.__name__}")
                    return cached
                
            except Exception as e:
                logger.warning(f"Redis GET error: {e}")
            
            logger.info(f"Cache MISS: {func.__name__}")
            result = func(*args, **kwargs)

            try:
                redis_client.setex(cache_key, ttl, result)
            except Exception as e:
                logger.warning(f"Redis SET error: {e}")
            return result
        return wrapper
    return decorator
# === TOOLS ===

# Tool: Real-time stock price retrieval
@tool
@redis_cache(ttl=60)
def get_stock_price(ticker: str) -> str:
    """Returns the current closing price for a stock ticker symbol (e.g., AAPL, NVDA)."""
    logger.info(f"Fetching stock price for ticker: {ticker}")
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period='1d')['Close'].iloc[-1]
        return str(round(price, 2))
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {str(e)}")
        return f"Error: Unable to fetch price for {ticker}"

# Tool: Historical stock price retrieval for a given date range
@tool
@redis_cache(ttl=43200)
def get_historical_stock_price(ticker: str, start_date: str, end_date: str, frequency: str = "monthly") -> str:
    """Returns historical closing prices aggregated by month, week, or quarter.
    
    Args:
        ticker: Stock symbol (e.g., AAPL, NVDA)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        frequency: 'daily' (max 90 days), 'weekly', 'monthly' (default), or 'quarterly'
    
    Use 'quarterly' for very long periods (5+ years), 'monthly' for 1-5 years (default), 
    'weekly' for 3-12 months, 'daily' for up to 3 months.
    """
    logger.info(f"Fetching historical prices: {ticker} ({start_date} to {end_date}, {frequency})")
    
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)
        
        if df.empty:
            return f"No data found for {ticker} in the specified date range."
        
        df = df[["Close"]]
        
        # Aggregate based on frequency to reduce tokens
        if frequency.lower() == "quarterly":
            df_resampled = df.resample('QE').last()
            df_resampled.index = df_resampled.index.strftime('%Y-Q%q')
            period_label = "Quarterly"
            max_points = 40  # ~10 anos
            
        elif frequency.lower() == "monthly":
            df_resampled = df.resample('ME').last()
            df_resampled.index = df_resampled.index.strftime('%Y-%m')
            period_label = "Monthly"
            max_points = 60  # ~5 anos
            
        elif frequency.lower() == "weekly":
            df_resampled = df.resample('W-FRI').last()
            df_resampled.index = df_resampled.index.strftime('%Y-%m-%d')
            period_label = "Weekly"
            max_points = 52  # ~1 ano
            
        else:  # daily
            if len(df) > 90:
                logger.warning(f"Daily data truncated to last 90 days for {ticker}")
                df = df.tail(90)
            df_resampled = df
            df_resampled.index = df_resampled.index.strftime('%Y-%m-%d')
            period_label = "Daily"
            max_points = 90
        
        # Limitar pontos totais
        if len(df_resampled) > max_points:
            logger.warning(f"{period_label} data truncated to last {max_points} points for {ticker}")
            df_resampled = df_resampled.tail(max_points)
        
        df_resampled['Close'] = df_resampled['Close'].round(2)
        
        # Retornar CSV puro (sem comentários)
        result = "Date,Close\n"
        result += df_resampled.to_csv(index=True, header=False)
        
        logger.info(f"Returned {len(df_resampled)} {period_label.lower()} data points for {ticker}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {str(e)}")
        return f"Error: Unable to fetch historical data for {ticker}"


# Tool: Retrieve a company's balance sheet data
@tool
@redis_cache(ttl=86400)
def get_balance_sheet(ticker: str) -> str:
    """Returns key balance sheet metrics for the last 3 fiscal years.
    
    Includes: Total Assets, Total Liabilities, Stockholders Equity, Current Assets, 
    Current Liabilities, Cash, Total Debt. Optimized for streaming responses.
    """
    logger.info(f"Fetching balance sheet for ticker: {ticker}")

    try: 
        stock = yf.Ticker(ticker)
        df = stock.balance_sheet.iloc[:, :3]  # Last 3 years
        
        # Key metrics only - reduces tokens significantly
        key_items = [
            'Total Assets', 
            'Total Liabilities Net Minority Interest',
            'Stockholders Equity', 
            'Current Assets', 
            'Current Liabilities',
            'Cash And Cash Equivalents',
            'Total Debt'
        ]
        
        available_items = df.index.intersection(key_items)
        
        if len(available_items) > 0:
            df_filtered = df.loc[available_items]
            result = f"{ticker} Balance Sheet (Key Metrics)\n"
            result += df_filtered.to_csv()
            return result
        else:
            # Fallback to top items
            logger.warning(f"Standard metrics not found for {ticker}, using top 8 rows")
            result = f"{ticker} Balance Sheet (Top Metrics)\n"
            result += df.head(8).to_csv()
            return result
            
    except Exception as e:
        logger.error(f"Error fetching balance sheet for {ticker}: {str(e)}")
        return f"Error: Unable to fetch balance sheet for {ticker}"

# Tool: Retrieve recent news for a stock
@tool
@redis_cache(ttl=3600)
def get_stock_news(ticker: str) -> str:
    """Returns the 5 most recent news articles for a stock ticker.
    
    Returns JSON with title, publisher, link, and publish date. Stream-optimized format.
    """
    logger.info(f"Fetching news for ticker: {ticker}")
    try:
        stock = yf.Ticker(ticker)
        
        # Tentar pegar news de múltiplas fontes
        raw_news = None
        try:
            raw_news = stock.news
            logger.info(f"Got {len(raw_news) if raw_news else 0} news items from stock.news")
        except Exception as e:
            logger.warning(f"stock.news failed: {e}")
        
        # Fallback: tentar .get_news() se disponível
        if not raw_news:
            try:
                raw_news = stock.get_news()
                logger.info(f"Got {len(raw_news) if raw_news else 0} news items from get_news()")
            except Exception as e:
                logger.warning(f"get_news() failed: {e}")
        
        # Se ainda não tem news, retornar vazio
        if not raw_news or len(raw_news) == 0:
            logger.warning(f"No news found for {ticker}")
            return json.dumps({"ticker": ticker, "articles": []})

        clean_news = []
        for n in raw_news[:5]:
            try:
                # Tentar múltiplos campos de timestamp
                ts = n.get('providerPublishTime') or n.get('publishTime') or n.get('timestamp')
                
                if ts:
                    # Se timestamp é string, tentar converter
                    if isinstance(ts, str):
                        try:
                            from dateutil import parser
                            dt = parser.parse(ts)
                            date_str = dt.strftime('%Y-%m-%d')
                        except:
                            date_str = ts[:10] if len(ts) >= 10 else "N/A"
                    else:
                        # Timestamp numérico
                        date_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                else:
                    date_str = "N/A"
                
                # Extrair campos com fallbacks
                title = n.get('title') or n.get('headline') or 'No title'
                publisher = n.get('publisher') or n.get('source') or 'Unknown'
                link = n.get('link') or n.get('url') or ''
                
                clean_news.append({
                    "title": str(title)[:90],
                    "publisher": str(publisher)[:20],
                    "link": str(link),
                    "date": date_str
                })
                
            except Exception as e:
                logger.warning(f"Error parsing news item: {e}")
                continue
        
        if not clean_news:
            logger.warning(f"No parseable news for {ticker}")
            return json.dumps({"ticker": ticker, "articles": []})
        
        logger.info(f"Returning {len(clean_news)} news articles for {ticker}")
        return json.dumps({
            "ticker": ticker,
            "articles": clean_news
        })
        
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {str(e)}")
        return json.dumps({"ticker": ticker, "articles": [], "error": str(e)[:50]})

# Tool: Perform web search requests via the Tavily API
@tool
@redis_cache(ttl=60)
def web_search(query: str) -> str:
    """Performs web search and returns top 3 results with title, snippet, and URL.
    
    Useful for recent market news, company information, earnings reports, and financial analysis.
    Results are optimized for streaming responses.
    """
    logger.info(f"Web search: {query[:60]}...")
    
    try:
        tavily_client = TavilyClient()
        response = tavily_client.search(query, search_depth="basic", max_results=3)
        
        # Extract and limit content for efficient streaming
        results = []
        for item in response.get('results', [])[:3]:
            results.append({
                'title': item.get('title', 'No title')[:100],
                'snippet': item.get('content', 'No content')[:250],  # Reduced to 250 chars
                'url': item.get('url', ''),
                'relevance': round(item.get('score', 0), 2)
            })
        
        return json.dumps({
            "query": query,
            "results": results,
            "count": len(results)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Web search error for '{query}': {str(e)}")
        return json.dumps({
            "query": query,
            "error": "Search failed",
            "results": []
        })


# Export all tools for easy import
__all__ = [
    'get_stock_price',
    'get_historical_stock_price', 
    'get_balance_sheet',
    'get_stock_news',
    'web_search'
]