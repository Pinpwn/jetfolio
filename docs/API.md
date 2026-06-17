# Stock Dashboard API Documentation

## Overview

The Stock Dashboard API provides programmatic access to portfolio data, market insights, and broker integrations. Built with FastAPI, it offers a RESTful interface for managing multi-platform stock portfolios.

**Version:** 1.0.0  
**Base URL:** `http://127.0.0.1:8000`  
**Protocol:** HTTP/HTTPS  
**Response Format:** JSON

## Table of Contents

- [Authentication](#authentication)
- [Portfolio Management](#portfolio-management)
- [Stock Operations](#stock-operations)
- [Theme Management](#theme-management)
- [News & Insights](#news--insights)
- [Broker Integration](#broker-integration)
- [Configuration](#configuration)
- [Error Handling](#error-handling)

---

## Authentication

### Zerodha OAuth

The API uses OAuth 2.0 for Zerodha broker authentication.

**Flow:**
1. User initiates login via `GET /api/zerodha/login`
2. User authorizes on Zerodha
3. Callback to `GET /api/zerodha/callback` exchanges token
4. Access token stored in Config table

**Status Check:**
```http
GET /api/zerodha/status
```

**Response:**
```json
{
  "api_key_configured": true,
  "authenticated": true,
  "user_id": "ST3620"
}
```

---

## Portfolio Management

### Sync Portfolio

Synchronizes portfolio from all connected broker platforms.

```http
POST /api/sync
```

**Response:**
```json
{
  "sync": {
    "status": "success",
    "synced_count": 8
  },
  "analysis": "completed"
}
```

### Get Portfolio Summary

Retrieves current portfolio overview with performance metrics.

```http
GET /api/portfolio
```

**Response:**
```json
{
  "total_value_inr": 450000.50,
  "total_invested": 400000.00,
  "absolute_return": 50000.50,
  "return_percent": 12.50,
  "day_change": 2500.00,
  "day_change_percent": 0.56
}
```

### Get Dashboard Data

Fetches comprehensive dashboard data including insights and timeline.

```http
GET /api/dashboard
```

**Response:**
```json
{
  "total_value": 450000.50,
  "day_change": 2500.00,
  "day_change_percent": 0.56,
  "top_performer": {
    "symbol": "AAPL",
    "change_percent": 5.2
  },
  "worst_performer": {
    "symbol": "VOO",
    "change_percent": -1.8
  }
}
```

---

## Stock Operations

### List All Stocks

Retrieves all stocks in the portfolio.

```http
GET /api/stocks
```

**Response:**
```json
[
  {
    "id": 1,
    "symbol": "RELIANCE",
    "name": "Reliance Industries",
    "quantity": 10.0,
    "average_price": 2400.00,
    "current_price": 2450.00,
    "currency": "INR",
    "platform": "zerodha",
    "asset_class": "EQUITY",
    "last_synced": "2025-12-09T00:00:00Z",
    "themes": ["Growth", "Energy"]
  }
]
```

### Get Stock Analysis

Fetches detailed analysis for a specific stock.

```http
GET /api/stocks/{symbol}/analysis
```

**Parameters:**
- `symbol` (path, required): Stock ticker symbol

**Example:**
```http
GET /api/stocks/AAPL/analysis
```

**Response:**
```json
{
  "symbol": "AAPL",
  "links": [
    {
      "name": "Screener.in",
      "url": "https://www.screener.in/company/AAPL/consolidated/"
    }
  ],
  "analyst_ratings": {
    "buy": 15,
    "hold": 8,
    "sell": 2,
    "consensus": "Bullish"
  },
  "latest_news": [
    {
      "title": "Apple announces new product line",
      "source": "Google News",
      "time": "Recently"
    }
  ],
  "sentiment": "Bullish"
}
```

---

## Theme Management

### List All Themes

Retrieves all investment themes with calculated metrics.

```http
GET /api/themes
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Tech Giants",
    "description": "Large-cap technology companies",
    "stock_count": 5,
    "total_value": 250000.00
  }
]
```

### Create Theme

Creates a new investment theme.

```http
POST /api/themes
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Dividend Growth",
  "description": "High dividend yield stocks with growth potential"
}
```

**Response:**
```json
{
  "id": 3,
  "name": "Dividend Growth",
  "description": "High dividend yield stocks with growth potential"
}
```

### Update Theme

Updates an existing theme.

```http
PUT /api/themes/{theme_id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Updated Theme Name",
  "description": "New description"
}
```

### Delete Theme

Deletes a theme (stocks remain, only theme association is removed).

```http
DELETE /api/themes/{theme_id}
```

**Response:**
```json
{
  "status": "deleted"
}
```

### Add Stock to Theme

Associates a stock with a theme.

```http
POST /api/themes/{theme_id}/stocks/{stock_id}
```

**Response:**
```json
{
  "status": "added"
}
```

### Remove Stock from Theme

Removes stock-theme association.

```http
DELETE /api/themes/{theme_id}/stocks/{stock_id}
```

**Response:**
```json
{
  "status": "removed"
}
```

---

## News & Insights

### Refresh Insights

Triggers news scraping and analysis for all stocks.

```http
POST /api/refresh
```

**Response:**
```json
{
  "status": "completed",
  "articles_added": 24
}
```

**Note:** This endpoint:
- Scrapes news from Google News RSS
- Performs deduplication
- Runs analysis engine for timeline events
- Clears LLM cache for fresh summaries

### Get News Articles

Retrieves news articles with optional filtering.

```http
GET /api/news?days={days}
```

**Parameters:**
- `days` (query, optional): Number of past days to fetch (default: 7)

**Response:**
```json
[
  {
    "id": 1,
    "stock_id": 1,
    "title": "Reliance Industries announces new venture",
    "summary": "Company expands into renewable energy...",
    "source": "Google News",
    "url": "https://news.google.com/...",
    "published_date": "2025-12-08T10:30:00Z",
    "scraped_at": "2025-12-09T00:00:00Z",
    "sentiment": "positive"
  }
]
```

### Get News for Specific Stock

```http
GET /api/news/{stock_id}
```

**Response:**
```json
[
  {
    "title": "Stock-specific news headline",
    "source": "Economic Times",
    "url": "https://...",
    "published_date": "2025-12-08T15:00:00Z"
  }
]
```

### Get Portfolio Insights

Retrieves winners, losers, and performance insights.

```http
GET /api/insights
```

**Response:**
```json
{
  "winners": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "pct_change": 12.5,
      "current_price": 175.30,
      "reason": "Strong quarterly earnings report and positive sector sentiment."
    }
  ],
  "losers": [
    {
      "symbol": "VOO",
      "name": "Vanguard S&P 500 ETF",
      "pct_change": -2.3,
      "current_price": 425.10,
      "reason": "Sector-wide correction and geopolitical headwinds affecting supply chain."
    }
  ]
}
```

---

## LLM-Powered Analysis

### Get Theme Summaries

AI-generated summaries for all themes (cached).

```http
GET /api/llm/theme-summaries
```

**Response:**
```json
[
  {
    "theme_id": 1,
    "theme": "Tech Giants",
    "summary": "Tech sector showing strong momentum...",
    "positives": [
      "Strong earnings growth",
      "Increased cloud adoption",
      "AI innovation leadership"
    ],
    "negatives": [
      "Regulatory scrutiny",
      "Valuation concerns",
      "Competition intensifying"
    ],
    "references": [],
    "cached": true
  }
]
```

### Get Portfolio Summary

AI-generated overall portfolio analysis (cached).

```http
GET /api/llm/portfolio-summary
```

**Response:**
```json
{
  "summary": "Your portfolio demonstrates balanced exposure...",
  "positives": [
    "Diversified across sectors",
    "Strong dividend coverage",
    "Growth potential intact"
  ],
  "negatives": [
    "Monitor market conditions",
    "Review periodically",
    "Rebalance as needed"
  ],
  "references": [],
  "cached": false
}
```

### Clear LLM Cache

Forces regeneration of cached summaries.

```http
POST /api/clear-llm-cache
```

**Response:**
```json
{
  "status": "cache_cleared"
}
```

---

## Broker Integration

### Zerodha Login

Initiates Zerodha OAuth flow.

```http
GET /api/zerodha/login
```

**Redirects to:** Zerodha login page

### Zerodha Callback

OAuth callback endpoint (called by Zerodha).

```http
GET /api/zerodha/callback?request_token={token}
```

**Response:** Redirects to `/?zerodha=connected`

### Zerodha Status

Checks authentication status.

```http
GET /api/zerodha/status
```

**Response:**
```json
{
  "api_key_configured": true,
  "authenticated": true,
  "user_id": "ST3620"
}
```

---

## Configuration

### Get Config Value

Retrieves a configuration value by key. Sensitive values (API keys, tokens) are masked for security.

```http
GET /api/config/{key}
```

**Example:**
```http
GET /api/config/perplexity_api_key
```

**Response:**
```json
{
  "key": "perplexity_api_key",
  "value": "pp...23 (Encrypted)",
  "is_encrypted": true
}
```

### Update Config Value

Sets or updates a configuration value. Sensitive keys containing "api_key", "api_secret", or "token" are automatically encrypted at rest and validated for format.

```http
PUT /api/config/{key}?value={value}
```

**Example:**
```http
PUT /api/config/perplexity_api_key?value=pplx-newkey123
```

**Response:**
```json
{
  "key": "perplexity_api_key",
  "value": "******** (Saved Encrypted)",
  "is_encrypted": true
}
```

### Get Application Logs

Retrieves recent application logs.

```http
GET /api/logs?lines={count}
```

**Parameters:**
- `lines` (query, optional): Number of log lines (default: 100)

**Response:**
```json
{
  "logs": "[2025-12-09 00:00:00] [INFO] Application started\n..."
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 404 | Not Found | Resource not found |
| 405 | Method Not Allowed | HTTP method not supported |
| 500 | Internal Server Error | Server-side error |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

**Zerodha Not Configured:**
```json
{
  "detail": "Zerodha API key not configured. Please add it in Settings."
}
```

**Theme Not Found:**
```json
{
  "detail": "Theme not found"
}
```

**Stock Already in Theme:**
```json
{
  "detail": "Stock already in this theme"
}
```

---

## Rate Limits

Currently, the API does not enforce rate limits. For production deployment, implement rate limiting based on:
- IP address
- User authentication
- Endpoint-specific limits

**Recommended Limits:**
- General endpoints: 100 req/min
- Sync operations: 10 req/min
- News scraping: 5 req/min

---

## Best Practices

1. **Caching:** Use LLM cache to minimize AI API calls and costs
2. **Pagination:** For large datasets, implement pagination (future enhancement)
3. **Background Jobs:** Use `/api/refresh` sparingly; consider scheduled jobs
4. **Error Handling:** Always check response status and handle errors gracefully
5. **Security:** Store API keys in Config table, never in client code

---

## Interactive API Docs

FastAPI provides automatic interactive documentation:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

These interfaces allow you to:
- Explore all endpoints
- Test API calls directly
- View request/response schemas
- Download OpenAPI specification

---

## Examples

### Complete Workflow Example

```bash
# 1. Configure Zerodha
curl -X PUT "http://127.0.0.1:8000/api/config/zerodha_api_key?value=YOUR_KEY"
curl -X PUT "http://127.0.0.1:8000/api/config/zerodha_api_secret?value=YOUR_SECRET"

# 2. Login to Zerodha (opens browser)
# Navigate to: http://127.0.0.1:8000/api/zerodha/login

# 3. Sync portfolio
curl -X POST "http://127.0.0.1:8000/api/sync"

# 4. Get dashboard
curl "http://127.0.0.1:8000/api/dashboard"

# 5. Create a theme
curl -X POST "http://127.0.0.1:8000/api/themes" \
  -H "Content-Type: application/json" \
  -d '{"name":"Growth Stocks","description":"High growth potential"}'

# 6. Add stock to theme (IDs from previous responses)
curl -X POST "http://127.0.0.1:8000/api/themes/1/stocks/1"

# 7. Get AI insights
curl "http://127.0.0.1:8000/api/llm/portfolio-summary"

# 8. Refresh news
curl -X POST "http://127.0.0.1:8000/api/refresh"

# 9. View news
curl "http://127.0.0.1:8000/api/news?days=7"
```

---

## Support

For issues or questions:
- Check interactive docs at `/docs`
- Review application logs at `/api/logs`
- Inspect database: `sqlite3 portfolio.db`

---

**Last Updated:** 2025-12-09  
**API Version:** 1.0.0
