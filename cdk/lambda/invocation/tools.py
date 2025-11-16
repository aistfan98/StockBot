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

@mcp.tool()
def check_recent_news(query = "Stock market recent news"):
    url = f"https://finnhub.io/api/v1/news?token={FINNHUB_API_KEY}"

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        news_items = r.json()
    except Exception as e:
        return {"Error calling Finnhub API": str(e)}

    trimmed = []
    for item in news_items[:10]:  # keep top 10 to avoid noise
        trimmed.append({
            "headline": item.get("headline"),
            "source": item.get("source"),
            "datetime": item.get("datetime"),
            "summary": item.get("summary"),
            "url": item.get("url")
        })

    return {"newsArticles": trimmed}

@mcp.tool()
def check_stock_price(stock_symbol):
    url = f"https://finnhub.io/api/v1/quote?token={FINNHUB_API_KEY}&symbol={stock_symbol}"

    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes
        priceData = response.json()
    except Exception as e:
        return {"Error calling Finnhub API": str(e)}

    return priceData["c"]

if __name__ == "__main__":
    mcp.run(transport="stdio")