# Dashboard Caching & Refresh Strategy

The Stock Dashboard utilizes a multi-layer caching strategy to balance performance with data freshness. Caches are primarily stored in the `Config` table (key-value store) or persisted in specific data models.

## Cached Elements List

| Element | Storage Location | Refresh Interval (TTL) | Trigger / Invalidation |
| :--- | :--- | :--- | :--- |
| **Weekly Insights** | `Config` table (`weekly_insights_cache`) | **6 Hours** | **Auto:** On access if >6h old.<br>**Manual:** `/api/insights?refresh=true` |
| **Portfolio AI Summary** | `Config` table (`portfolio_summary`) | **6 Hours** | **Auto:** On access if >6h old.<br>**Manual:** `/api/llm/portfolio-summary?refresh=true` |
| **Theme Summaries** | `Config` table (`theme_summary_{id}`) | **Indefinite** | **Invalidation:** Cleared automatically when stock data is modified (Buy/Sell) via `/api/clear-llm-cache`. |
| **Stock Prices** | `Stock` table columns | **On-Demand** | **Manual:** `/api/sync` triggers `PriceFetcher`. |
| **News Feed** | `NewsArticle` table | **On-Demand** | **Manual:** `/api/refresh` or `/api/sync` triggers `NewsScraperService`. |
| **Timeline Events** | `TimelineEvent` table | **Event-Driven** | Generated post-sync or post-refresh if price movement > **3%**. Deduplicated daily. |
| **Zerodha Token** | `Config` table (`zerodha_access_token`) | **Session-Based** | Valid until Zerodha session expires (usually daily). Updated via `/api/zerodha/login`. |

## Detailed Breakdown

### 1. Weekly Insights (Smart Cache)
- **Goal:** Provide fast access to "Winners & Losers" without re-analyzing the entire market on every page load.
- **Logic:**
    - Checks `weekly_insights_cache` key.
    - If `updated_at` < 6 hours ago, serve cache.
    - If older or `refresh=true`, trigger background generation (`AnalysisEngine.generate_insights`).
    - **Note:** Returns "stale" data immediately while regenerating in background if expired.

### 2. AI Summaries (Cost Optimization)
- **Goal:** Minimize expensive LLM (Perplexity) API calls.
- **Theme Summaries:** Generated once and stored.
- **Portfolio Summary:** Re-generated only every 6 hours or when explicitly requested.
- **Invalidation Cache Strategy:** Any data mutation (adding stocks, selling) calls `clear_llm_cache` to ensure the AI doesn't hallucinate about old holdings.

### 3. Background Sync
- **Process:** `/api/sync` and `/api/refresh` immediately return a success response to the UI while spinning up `BackgroundTasks`.
- **Flow:**
    1.  Fetch Prices (YFinance).
    2.  Scrape News (Google/YFinance).
    3.  Generate Insights (Analysis).
    4.  Update Caches.
