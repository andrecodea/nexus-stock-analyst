# Creates the tools that the agent will use during execution.

# Imports logging and environment variable importing components
from dotenv import load_dotenv
import logging

# Imports the tool components 
import yfinance as yf
from langchain.tools import tool
from tavily import TavilyClient

# Environment variable loading and logger config
load_dotenv()
logger = logging.getLogger(__name__)

# === TOOLS ===

# Tool: Real-time stock price retrieval
@tool (
        "get_stock_price", 
        description="Returns real-time stock price based on ticker symbol. e.g. NVDA"
        )
def get_stock_price(ticker: str):
    """
    Returns the real-time ticker value.
    
    :param ticker: ticker symbol, e.g. NVDA.
    :type ticker: str
    """
    logger.info(f"Fetching stock price for ticker: {ticker}")
    stock = yf.Ticker(ticker)
    return stock.history()['Close'].iloc[-1]

# Tool: Historical stock price retrieval for a given date range
@tool (
        "get_historical_stock_price", 
        description="Returns summarized historical stock price data based on a ticker symbol e.g. NVDA, and a time range. Includes summary statistics and monthly data points to minimize token usage."
        )
def get_historical_stock_price(ticker:str, start_date: str, end_date:str):
        """
        Returns historical ticker price based on a time range with optimized output.

        :param ticker: Ticker symbol, e.g. NVDA
        :type ticker: str
        :param start_date: Time range start date
        :type start_date: str
        :param end_date: Time range end date.
        :type end_date: str
        """
        logger.info(f"Fetching historical stock price for ticker: {ticker}")
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)
        
        if df.empty:
            return {"error": "No data available for the specified period"}
        
        # Return optimized summary instead of full data
        return {
            "ticker": ticker,
            "period": f"{start_date} to {end_date}",
            "summary": {
                "start_price": round(float(df['Close'].iloc[0]), 2),
                "end_price": round(float(df['Close'].iloc[-1]), 2),
                "high": round(float(df['High'].max()), 2),
                "low": round(float(df['Low'].min()), 2),
                "avg_volume": int(df['Volume'].mean()),
                "total_return_pct": round(float((df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100), 2)
            },
            # Provide monthly data points for trend analysis (much smaller than daily)
            "monthly_data": {
                str(date.date()): round(float(value), 2) 
                for date, value in df['Close'].resample('ME').last().items()
            },
            "data_points": len(df)
        }

# Tool: Retrieve a company's balance sheet data
@tool (
        "get_balance_sheet", 
        description="Returns key balance sheet metrics of a ticker symbol, e.g. NVDA. Returns summarized data to minimize token usage."
        )
def get_balance_sheet(ticker: str):
     
     """
     Returns key balance sheet metrics of a ticker symbol, e.g. NVDA.
     
     :param ticker: Ticker symbol e.g. NVDA
     :type ticker: str
     """
     logger.info(f"Fetching balance sheet for ticker: {ticker}")
     stock = yf.Ticker(ticker)
     bs = stock.balance_sheet
     
     if bs.empty:
         return {"error": "No balance sheet data available"}
     
     # Define key metrics to extract (most relevant for analysis)
     key_metrics = [
         'Total Assets',
         'Current Assets', 
         'Cash And Cash Equivalents',
         'Total Liabilities Net Minority Interest',
         'Current Liabilities',
         'Total Debt',
         'Stockholders Equity',
         'Net Debt'
     ]
     
     # Get latest period only (most recent column)
     latest = bs.iloc[:, 0]
     
     # Extract available key metrics
     filtered_metrics = {}
     for metric in key_metrics:
         if metric in latest.index:
             value = latest[metric]
             # Convert to float and handle NaN
             if value is not None and str(value) != 'nan':
                 filtered_metrics[metric] = float(value)
     
     return {
         "ticker": ticker,
         "date": bs.columns[0].strftime('%Y-%m-%d'),
         "key_metrics": filtered_metrics,
         "currency": "USD"
     }

    

# Tool: Retrieve recent news items related to a ticker symbol
@tool (
        "get_stock_news", 
        description="Returns the latest ticker symbol related news e.g. NVDA. Limited to 5 most recent articles to minimize token usage."
        )
def get_stock_news(ticker: str):
    """
    Returns recent news related to the ticker (limited to 5 articles).
    
    :param ticker: Ticker symbol (e.g. NVDA)
    :type ticker: str
    """
    logger.info(f"Fetching news for ticker: {ticker}")
    stock = yf.Ticker(ticker)
    news = stock.news
    
    if not news:
        return {"message": "No recent news available"}
    
    # Limit to 5 most recent articles and extract only essential fields
    limited_news = []
    for article in news[:5]:
        limited_news.append({
            "title": article.get("title", ""),
            "publisher": article.get("publisher", ""),
            "link": article.get("link", ""),
            "published_date": article.get("providerPublishTime", ""),
            # Only include summary if available and short
            "summary": article.get("summary", "")[:200] if article.get("summary") else ""
        })
    
    return {
        "ticker": ticker,
        "news_count": len(limited_news),
        "articles": limited_news
    }


# Tool: Perform web search requests via the Tavily API
@tool (
     "web_search",
     description="Uses Tavily API to search the web. Returns summarized results to minimize token usage."
)
def web_search(query: str):
     """
     Return a web search result through the Tavily API based on a query determined by the agent.
     Results are optimized to reduce token usage.
     
     :param query: Web search query
     :type query: str
     """
     logger.info(f"Executing web search for query: {query[:50]}...")  # Logs the first 50 chars 
     tavily_client = TavilyClient()
     results = tavily_client.search(query, max_results=5)  # Limit to 5 results
     
     # Extract only essential fields to reduce token usage
     if isinstance(results, dict) and 'results' in results:
         optimized_results = []
         for result in results['results'][:5]:
             optimized_results.append({
                 "title": result.get("title", ""),
                 "url": result.get("url", ""),
                 "content": result.get("content", "")[:300],  # Limit content to 300 chars
                 "score": result.get("score", 0)
             })
         return {
             "query": query,
             "results_count": len(optimized_results),
             "results": optimized_results
         }
     
     return results