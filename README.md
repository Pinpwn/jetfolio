# Stock Dashboard - Setup & Security Guide

## Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# If requirements.txt doesn't exist, install manually:
pip install fastapi uvicorn sqlmodel pydantic requests beautifulsoup4 kiteconnect cryptography python-jose
```

```

### 2. Local AI Setup (Optional)

To use local LLMs (Ollama) for privacy-focused, offline analysis:

**Requirements:**
- Ollama installed (or Docker & Docker Compose)
- **RAM:** Minimum 8GB (Recommended 16GB)

**Setup:**
The easiest way is to run Ollama locally or via Docker:

```bash
# Using Docker Compose
docker-compose up -d
```

Once running, go to **Settings > AI Provider Configuration** in the dashboard to switch to "Local LLM" and provide your Ollama API URL (default: `http://localhost:8888/api/generate`).

This will allow the dashboard to generate AI insights and perform sentiment analysis using your local model.

### 3. Security Setup (IMPORTANT for Production)

#### Encryption at Rest (Enforced)

**Required for API key and token security:**

The application now automatically encrypts sensitive keys (api_key, api_secret, token) at rest using AES-256-GCM. 

```bash
# Generate and set encryption key
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Or add to .env file (recommended):
echo "ENCRYPTION_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" >> .env
```

**⚠️ WARNING:** 
- Store this key securely - losing it means losing access to encrypted API keys.
- If not set, the app will generate a temporary session-based key for development, which means keys won't persist across restarts.
- Never commit the key to version control.

#### Data Sanitization

- All user-generated content is sanitized for XSS.
- API endpoints mask sensitive values in responses.
- API key format validation is enforced.

#### For Production Deployment

1. **Enable HTTPS:**
   ```bash
   # Use environment variable
   export USE_HTTPS=true
   
   # Or run behind nginx with SSL certificate
   ```

2. **Set JWT Secret (for future authentication):**
   ```bash
   export JWT_SECRET_KEY=$(openssl rand -hex 32)
   ```

3. **Configure CORS (if frontend is separate domain):**
   ```python
   # In main.py
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your frontend.com"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

### 3. Run the Server

```bash
# Development
./run_server.sh

# Or manually:
python -m uvicorn backend.main:app --reload --port 8000

# Production (with HTTPS):
python -m uvicorn backend.main:app --host 0.0.0.0 --port 443 --ssl-keyfile=/path/to/key.pem --ssl-certfile=/path/to/cert.pem
```

### 4. Access the Application

- **Dashboard:** http://127.0.0.1:8000
- **API Docs:** http://127.0.0.1:8000/docs
- **Alternative Docs:** http://127.0.0.1:8000/redoc

---

## Security Configuration

### Overview

The application implements security measures at multiple levels:

1. **Data Encryption** - API keys encrypted at rest
2. **Security Headers** - HTTP headers prevent common web attacks
3. **Input Validation** - API key format validation
4. **XSS Prevention** - Frontend utilities for safe HTML rendering
5. **Generic Errors** - Avoid information disclosure

### Current Security Status

✅ **Implemented:**
- Encryption framework for sensitive data
- Security headers middleware
- Input sanitization utilities (frontend & backend)
- API key format validation
- Generic error messages
- XSS prevention utilities

⚠️ **Pending (Required for Production):**
- User authentication/authorization (JWT)
- HTTPS/TLS enforcement
- CSRF protection
- Rate limiting
- Database encryption at rest

### Security Checklist

Before deploying to production:

- [ ] Set `ENCRYPTION_KEY` environment variable
- [ ] Enable HTTPS/TLS (port 443 with SSL certificate)
- [ ] Configure CORS for your domain
- [ ] Set restrictive database file permissions (`chmod 600 portfolio.db`)
- [ ] Implement authentication (see SECURITY_ASSESSMENT.md)
- [ ] Add CSRF protection
- [ ] Enable rate limiting
- [ ] Review and test all API endpoints
- [ ] Perform security audit

---

## Environment Variables

| Variable          | Required   | Description                        | Example               |
| ----------------- | ---------- | ---------------------------------- | --------------------- |
| `ENCRYPTION_KEY`  | Yes (Prod) | Fernet encryption key for API keys | `7x9K...base64...`    |
| `JWT_SECRET_KEY`  | Future     | JWT token signing key              | `hex-string...`       |
| `USE_HTTPS`       | Prod       | Enable HTTPS enforcement           | `true`                |
| `ALLOWED_ORIGINS` | Optional   | CORS allowed origins               | `https://example.com` |

---

## Development vs Production

### Development (Current Setup)

```bash
# .env.development
ENCRYPTION_KEY=temp-dev-key-do-not-use-in-prod
DEBUG=true
```

- Auto-generates encryption key if not set (data won't persist across restarts)
- HTTP allowed on localhost
- Detailed error messages
- No authentication required

### Production (Recommended)

```bash
# .env.production
ENCRYPTION_KEY=<secure-key-from-above>
JWT_SECRET_KEY=<secure-jwt-key>
USE_HTTPS=true
ALLOWED_ORIGINS=https://yourdomain.com
DEBUG=false
```

- Requires encryption key (fails without it)
- HTTPS enforced
- Generic error messages
- Authentication required
- Rate limiting enabled
- Security headers active

---

## API Security

### Authentication (Future Implementation)

The application is designed to support JWT-based authentication:

```python
# Example endpoint with authentication
@app.get("/api/stocks")
async def get_stocks(current_user: str = Depends(get_current_user)):
    # Only authenticated users can access
    return stocks
```

To implement:
1. Uncomment authentication code in `backend/auth.py`
2. Add login/logout endpoints
3. Protect sensitive endpoints with `Depends(get_current_user)`

### API Key Management

**Storing API Keys:**

```python
from backend.security import get_secure_config

# Encrypt before storing
secure_config = get_secure_config()
encrypted_key = secure_config.encrypt("your-api-key")

# Store in database
config = Config(key="api_key", encrypted_value=encrypted_key)
```

**Best Practices:**
- Never hardcode API keys in code
- Use environment variables for non-user-specific keys
- Rotate keys regularly
- Revoke compromised keys immediately

---

## Frontend Security

### XSS Prevention

**Always use security utilities when rendering user content:**

```javascript
// ✅ SAFE - Using security utilities
const { escapeHtml, createSafeElement } = window.securityUtils;

// Method 1: Escape and render
div.innerHTML = `<h4>${escapeHtml(article.title)}</h4>`;

// Method 2: Use textContent (safest)
const heading = createSafeElement('h4', article.title);
div.appendChild(heading);

// ❌ UNSAFE - Direct innerHTML with user data
div.innerHTML = `<h4>${article.title}</h4>`;  // XSS vulnerability!
```

---

## Troubleshooting

### Encryption Key Issues

**Problem:** "ENCRYPTION_KEY not set" warning

**Solution:**
```bash
# Set the key
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Verify it's set
echo $ENCRYPTION_KEY
```

### HTTPS Certificate Errors

**Problem:** "SSL certificate verification failed"

**Solution:**
- For development: Use self-signed certificate
- For production: Use Let's Encrypt free SSL certificates

```bash
# Generate self-signed cert (development only)
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

### Security Headers Blocking Resources

**Problem:** Content Security Policy blocking external resources

**Solution:** Update CSP in `backend/middleware.py`:

```python
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self' https://trusted-cdn.com; "
    # ... add your trusted domains
)
```

---

## Additional Resources

- **Security Assessment:** See `SECURITY_ASSESSMENT.md`
- **API Documentation:** See `API.md`
- **Interactive API Docs:** http://127.0.0.1:8000/docs

---

## Support

For security issues, please:
1. Review `SECURITY_ASSESSMENT.md`
2. Check application logs: `tail -f logs/app.log`
3. Test with API docs: http://127.0.0.1:8000/docs

**Never** share API keys, tokens, or the encryption key in support requests!
