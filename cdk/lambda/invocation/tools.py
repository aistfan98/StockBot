import os, json
import requests
import boto3
from mcp.server.fastmcp import FastMCP

secrets_manager_client = boto3.client("secretsmanager", region_name="us-east-1")
mcp = FastMCP("lambda-mcp")

def get_finnub_api_key():
    secret_arn = os.environ["FINNHUB_API_KEY_SECRET_ARN"]
    response = secrets_manager_client.get_secret_value(SecretId=secret_arn)
    return response["SecretString"]

FINNHUB_API_KEY = get_finnub_api_key()

def call_finnhub(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        json_response = r.json()
    except Exception as e:
        return {"Error calling Finnhub API": str(e)}
    return json_response

# This MCP tool retrieves the latest market news from Finnhub using the /news endpoint.
# It requires a "category" parameter (default = general), which must be one of:
#   - "general"  → broad market news
#   - "forex"    → currency and FX-related news
#   - "crypto"   → cryptocurrency news
#   - "merger"   → M&A activity and corporate restructuring news
#
# Optional parameter:
#   - min_id: return only news items with an ID greater than this value (default = 0).
#            This is useful for pagination or fetching only new updates since the last call.
#
# The endpoint does *not* return historical news beyond what Finnhub provides, and the
# agent should call this tool only when it needs up-to-date headlines for market sentiment
# or narrative context. The tool returns an array of news objects containing headlines,
# summaries, timestamps, and related tickers.
#
# Example API call format (performed internally by this tool):
#   /news?category=general
#   /news?category=forex&minId=10
#
# The agent should choose the category based on what type of market news it needs and
# optionally pass a minId if it wants only new articles since the last retrieval.
@mcp.tool()
def check_overall_market_news(category = "general", min_id = 0):
    url = f"https://finnhub.io/api/v1/news?token={FINNHUB_API_KEY}&category={category}&minId={min_id}"

    news_items = call_finnhub(url)

    trimmed = []
    for item in news_items[:25]:  # keep top 25 to avoid noise
        trimmed.append({
            "headline": item.get("headline"),
            "source": item.get("source"),
            "datetime": item.get("datetime"),
            "summary": item.get("summary"),
            "url": item.get("url")
        })

    return {"newsArticles": trimmed}

# This MCP tool retrieves company-specific news from Finnhub using the /company-news
# endpoint. The endpoint requires a stock ticker and a date range, returning all news
# items Finnhub has for that company between the given dates.
#
# Required parameter:
#   - stock_symbol: the company ticker symbol (e.g., "AAPL").
#   - fromDay: start date in YYYY-MM-DD format.
#   - toDay:   end date in YYYY-MM-DD format.
#
# Notes for the agent:
# - Both "from" and "to" dates are mandatory for Finnhub; omitting either will return
#   no data. If unsure, use recent dates (e.g., past week or past month).
# - Finnhub’s documentation states that the /company-news endpoint only supports
#   North American companies. If the agent receives empty results, the symbol may be
#   outside that coverage.
# - Use this tool when the task requires news about a **specific company**, not general
#   market sentiment.
# - Returned items typically include: headline, summary, timestamp, source, and URL.
#
# Example API call format (performed internally by this tool):
#   /company-news?symbol=AAPL&from=2025-05-15&to=2025-06-20
#
# The agent should set a date range based on context:
#   - Narrow window (few days) → recent sentiment or events.
#   - Wider window (months/year) → historical catalysts or pattern analysis.
@mcp.tool()
def check_company_specific_news(stock_symbol, fromDay, toDay):
    url = f"https://finnhub.io/api/v1/company-news?token={FINNHUB_API_KEY}&symbol={stock_symbol}&from={fromDay}&to={toDay}"

    news_items = call_finnhub(url)

    trimmed = []
    for item in news_items[:25]:  # keep top 25 to avoid noise
        trimmed.append({
            "headline": item.get("headline"),
            "source": item.get("source"),
            "datetime": item.get("datetime"),
            "summary": item.get("summary"),
            "url": item.get("url")
        })

    return {"newsArticles": trimmed}

# This MCP tool retrieves the real-time stock quote for a given symbol using
# Finnhub’s /quote endpoint. The tool returns all key price data provided
# by Finnhub for U.S. stocks.
#
# Required parameter:
#   - stock_symbol: the ticker symbol of the company (e.g., "AAPL", "MSFT").
#
# Notes for the agent:
# - This tool returns the following fields (all floats unless noted):
#     - c: Current price (latest traded price)
#     - h: High price of the day
#     - l: Low price of the day
#     - o: Open price of the day
#     - pc: Previous close price
#     - t: Timestamp (Unix time) of the current price
#
# - The agent should use these fields as follows:
#     - "c" → primary current stock price for decision-making or reporting
#     - "h"/"l" → intraday range (volatility)
#     - "o" → opening price for gap analysis
#     - "pc" → previous close for daily change calculations
#     - "t" → reference time for the quote (important if combining with other real-time data)
#
# Example API call format (performed internally by this tool):
#   /quote?symbol=AAPL
#
# The agent should ensure the symbol is valid and typically U.S.-listed to avoid
# missing or unreliable data.
@mcp.tool()
def check_stock_price(stock_symbol):
    url = f"https://finnhub.io/api/v1/quote?token={FINNHUB_API_KEY}&symbol={stock_symbol}"

    price_data = call_finnhub(url)

    return price_data

# This MCP tool retrieves a curated set of key financial metrics for a given company
# using Finnhub’s /stock/metric endpoint. The tool fetches all metrics from the API
# but returns only a small, important subset to reduce payload size and avoid
# context-window overflow during reasoning.
#
# Required parameter:
#   - stock_symbol: the ticker symbol of the company (e.g., "AAPL").
#
# Notes for the agent:
# - The full API response contains:
#     - "metric": key-value pairs of financial ratios and metrics
#     - "metricType": the type of metric retrieved (here "all")
#     - "series": historical time-series data for each metric (not included in this tool)
#     - "symbol": company ticker
#
# - This tool returns the following trimmed metrics (all numeric unless noted):
#     - peTTM: Price-to-Earnings ratio (trailing twelve months)
#     - pegTTM: Price/Earnings-to-Growth ratio
#     - psTTM: Price-to-Sales ratio
#     - operatingMarginTTM: Operating margin (TTM)
#     - grossMarginTTM: Gross margin (TTM)
#     - roeTTM: Return on equity (TTM)
#     - netProfitMarginTTM: Net profit margin (TTM)
#     - revenueGrowthTTMYoy: Revenue growth year-over-year (TTM)
#     - epsGrowthTTMYoy: Earnings per share growth YoY (TTM)
#     - debtToEquity: Total debt / total equity (annual)
#     - currentRatio: Current ratio (annual)
#     - freeCashFlowPerShareTTM: Free cash flow per share (TTM)
#     - marketCap: Market capitalization
#     - 52WeekHigh / 52WeekLow: High and low over the past 52 weeks
#     - beta: Beta coefficient (volatility relative to market)
#
# - Use this tool when the task requires core financial metrics for investment
#   analysis, valuation, or risk assessment. The historical series is omitted
#   because LLM reasoning is better on condensed summaries rather than long arrays.
#
# Example API call format (performed internally by this tool):
#   /stock/metric?symbol=AAPL&metric=all
#
# The agent should provide a valid U.S. ticker symbol. Returned metrics can be used
# for calculations, comparisons, or decision-making.
@mcp.tool()
def check_company_financials(stock_symbol):
    url = f"https://finnhub.io/api/v1/stock/metric?token={FINNHUB_API_KEY}&symbol={stock_symbol}&metric=all"

    full_data = call_finnhub(url)

    # If Finnhub fails or returns nothing
    if not full_data or "metric" not in full_data:
        return {"error": "No data returned from Finnhub"}

    metrics = full_data["metric"]

    # Define only the metrics your AI bot needs
    desired_fields = {
        "peTTM": metrics.get("peTTM"),
        "pegTTM": metrics.get("pegTTM"),
        "psTTM": metrics.get("psTTM"),
        "operatingMarginTTM": metrics.get("operatingMarginTTM"),
        "grossMarginTTM": metrics.get("grossMarginTTM"),
        "roeTTM": metrics.get("roeTTM"),
        "netProfitMarginTTM": metrics.get("netProfitMarginTTM"),
        "revenueGrowthTTMYoy": metrics.get("revenueGrowthTTMYoy"),
        "epsGrowthTTMYoy": metrics.get("epsGrowthTTMYoy"),
        "debtToEquity": metrics.get("totalDebt/totalEquityAnnual"),
        "currentRatio": metrics.get("currentRatioAnnual"),
        "freeCashFlowPerShareTTM": metrics.get("cashFlowPerShareTTM"),
        "marketCap": metrics.get("marketCapitalization"),
        "52WeekHigh": metrics.get("52WeekHigh"),
        "52WeekLow": metrics.get("52WeekLow"),
        "beta": metrics.get("beta"),
    }

    return desired_fields

if __name__ == "__main__":
    mcp.run(transport="stdio")