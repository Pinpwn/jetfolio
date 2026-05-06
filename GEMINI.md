# Project Overview: Stock Helper

Stock Helper is a comprehensive stock portfolio management and analysis dashboard built with FastAPI. it integrates with various brokers (like Zerodha via Kite Connect) and leverages AI (local Ollama or cloud providers like Perplexity/Groq) to provide sentiment analysis, news scraping, and portfolio insights.

## Main Technologies
- **Backend:** Python, FastAPI, SQLModel (ORM), Pydantic (Validation)
- **Database:** SQLite (managed via SQLModel)
- **Frontend:** HTML/CSS/JS (Server-side rendering via Jinja2 templates)
- **AI/LLM:** Ollama (local), Perplexity, Groq
- **Broker APIs:** KiteConnect (Zerodha)
- **Data Sources:** yfinance, custom scrapers (BeautifulSoup4)
- **Security:** AES-256-GCM (via `cryptography` library) for encryption at rest

## Architecture
- `backend/`: Core logic including models, database config, and security.
  - `adapters/`: Broker-specific integration (Zerodha, Vested).
  - `services/`: Specialized modules for price fetching, currency conversion, scraping, and LLM interaction.
  - `sync_engine.py`: Handles data synchronization from external platforms.
  - `analysis_engine.py`: Detects significant events and generates insights.
- `static/`: Frontend assets (CSS, JS, images).
- `templates/`: Jinja2 templates for the web interface.
- `scripts/`: Utility scripts for database migrations or data processing.

## Building and Running

### Prerequisites
- Python 3.9+
- Virtual environment (recommended)

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up encryption key (Required for sensitive data storage)
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### Running the Server
```bash
# Using the startup script
./run_server.sh

# Or manually via uvicorn
python -m uvicorn backend.main:app --reload --port 8000
```

### Testing
- [TODO] The `tests/` directory is currently empty. Use `pytest` for future test implementations.

## Development Conventions

### Coding Style
- **Strict Typing:** Use Python type hints for all function signatures and variable declarations.
- **Docstrings:** Follow Google/Sphinx format for all classes and functions.
- **Naming:** Use descriptive, intention-revealing names (e.g., `calculate_portfolio_value()` instead of `calc_val()`).
- **Clean Code:** Adhere to SOLID and DRY principles.

### Security Standards
- **Encryption:** Sensitive values (API keys, tokens) must be encrypted at rest using AES-256-GCM.
- **Input Validation:** Use Pydantic models for strict schema validation of all API inputs.
- **Zero-Trust:** Treat all external data as potentially malicious; sanitize HTML and use parameterized queries.
- **Generic Errors:** Avoid exposing internal system details in API error responses.

### Error Handling
- Use `try-except-finally` blocks extensively.
- Avoid bare `except:` blocks.
- Log errors with context for debugging, but return user-friendly messages.

### AI Guidelines
- Prefer non-blocking I/O for LLM and external API calls.
- Implement caching (TTL-based) for expensive AI-generated summaries to reduce latency and costs.
