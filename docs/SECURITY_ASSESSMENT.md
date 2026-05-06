# Security Assessment Report
## Stock Dashboard Application

**Assessment Date:** 2025-12-09  
**Version:** 1.0.0  
**Scope:** Full codebase analysis including backend, frontend, and API endpoints

---

## Executive Summary

This security assessment identifies vulnerabilities, security concerns, and recommendations for the Stock Dashboard application. The application handles sensitive financial data and broker API credentials, requiring robust security measures for production deployment.

**Overall Risk Level:** 🟡 **MEDIUM-HIGH**

**Critical Findings:** 3  
**High Priority:** 5  
**Medium Priority:** 4  
**Low Priority:** 3

---

## Critical Vulnerabilities

### 1. 🔴 CRITICAL: Plaintext API Key Storage
**Location:** `backend/models.py` (Config model), `portfolio.db`  
**Risk:** Data Breach, Credential Theft  
**CVSS Score:** 9.1 (Critical)

**Issue:**
```python
# backend/models.py:193
Security Note:
    Sensitive keys (API tokens) are stored in plaintext in SQLite.
```

All API credentials are stored unencrypted in SQLite database:
- Zerodha API keys and secrets
- Perplexity API keys
- OAuth access tokens

**Impact:**
- Anyone with database file access can steal API credentials
- Compromised credentials allow unauthorized portfolio access
- Potential financial fraud through broker APIs

**Recommendation:**
```python
# Use encryption for sensitive data
from cryptography.fernet import Fernet
import os

class SecureConfig(SQLModel, table=True):
    key: str = Field(primary_key=True)
    encrypted_value: bytes  # Encrypted instead of plaintext
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def value(self):
        cipher = Fernet(os.getenv('ENCRYPTION_KEY'))
        return cipher.decrypt(self.encrypted_value).decode()
```

**Alternative:** Use environment variables or secret management services (AWS Secrets Manager, HashiCorp Vault)

---

### 2. 🔴 CRITICAL: No Authentication/Authorization
**Location:** All API endpoints in `backend/main.py`  
**Risk:** Unauthorized Access, Data Exposure  
**CVSS Score:** 8.9 (High)

**Issue:**
```python
# No authentication on sensitive endpoints
@app.get("/api/stocks")  # Anyone can access
@app.get("/api/dashboard")  # No auth required
@app.put("/api/config/{key}")  # Anyone can change config!
```

**Impact:**
- Anyone on the network can access portfolio data
- Attackers can modify configuration (API keys, settings)
- No user isolation in multi-user scenarios
- API can be scraped or abused

**Recommendation:**
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/stocks")
def get_stocks(session: Session = Depends(get_session), 
               user: dict = Depends(verify_token)):
    # Now protected
    stocks = session.exec(select(Stock)).all()
    return stocks
```

---

### 3. 🔴 CRITICAL: Cross-Site Scripting (XSS) Vulnerabilities
**Location:** `static/js/app.js`, `static/js/app_v7.js`, `static/js/app_v8.js`  
**Risk:** Session Hijacking, Malicious Script Injection  
**CVSS Score:** 7.3 (High)

**Issue:**
```javascript
// Multiple instances of innerHTML with unsanitized data
div.innerHTML = `
    <h4>${article.title}</h4>  // User-controlled data!
    <p>${article.summary}</p>
`;

// Line 794 in app.js
div.innerHTML = `
    <div class="item-info">
        <h4>${article.title}</h4>  // XSS vulnerability
```

**Attack Scenario:**
1. Malicious news source returns title: `<img src=x onerror="alert('XSS')">`
2. Frontend renders unsanitized HTML
3. Malicious script executes in user's browser
4. Session tokens/cookies stolen

**Impact:**
- Cookie/session theft
- Keylogging
- Phishing attacks
- Account takeover

**Recommendation:**
```javascript
// Use textContent instead of innerHTML for user data
const titleEl = document.createElement('h4');
titleEl.textContent = article.title;  // Safe from XSS

// Or use DOMPurify library
import DOMPurify from 'dompurify';
div.innerHTML = DOMPurify.sanitize(`<h4>${article.title}</h4>`);
```

---

## High Priority Issues

### 4. 🟠 HIGH: SQL Injection Risk (Low likelihood with SQLModel)
**Location:** `backend/main.py`, various queries  
**Risk:** Database Manipulation  
**CVSS Score:** 6.5 (Medium)

**Issue:**
While SQLModel provides protection, custom queries could be vulnerable:
```python
# Potential risk if ever using raw SQL
session.exec(select(Config).where(Config.key.like("%summary%")))  # OK
# But avoid: session.execute(f"SELECT * FROM config WHERE key LIKE '%{user_input}%'")  # DANGEROUS
```

**Status:** Currently protected by SQLModel ORM, but requires vigilance.

**Recommendation:**
- Never use f-strings or string concatenation for queries
- Always use parameterized queries
- Use SQLModel/SQLAlchemy abstractions

---

### 5. 🟠 HIGH: No HTTPS/TLS
**Location:** Server configuration  
**Risk:** Man-in-the-Middle Attacks  
**CVSS Score:** 7.4 (High)

**Issue:**
```bash
# run_server.sh runs on HTTP only
python -m uvicorn backend.main:app --port 8000
```

**Impact:**
- Credentials transmitted in cleartext
- OAuth tokens intercepted
- Session hijacking on public networks

**Recommendation:**
```python
# For production, use HTTPS
# Option 1: Run behind nginx with SSL
# Option 2: Use Uvicorn with SSL

import ssl
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain('/path/to/cert.pem', '/path/to/key.pem')

uvicorn.run(app, host="0.0.0.0", port=443, ssl=ssl_context)
```

---

### 6. 🟠 HIGH: No CSRF Protection
**Location:** All POST/PUT/DELETE endpoints  
**Risk:** Cross-Site Request Forgery  
**CVSS Score:** 6.8 (Medium)

**Issue:**
```python
# No CSRF tokens on state-changing endpoints
@app.post("/api/sync")
@app.put("/api/config/{key}")
@app.delete("/api/themes/{theme_id}")
```

**Attack Scenario:**
1. User logged into dashboard
2. Visits malicious site
3. Malicious site sends POST request to `/api/themes/{id}` (delete theme)
4. Browser includes session cookies
5. Theme deleted without user consent

**Recommendation:**
```python
from fastapi_csrf_protect import CsrfProtect

@app.post("/api/sync")
async def sync(csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf_in_cookies(request)
    # Process sync
```

---

### 7. 🟠 HIGH: Exposed Error Messages
**Location:** `backend/main.py`, error handling  
**Risk:** Information Disclosure  
**CVSS Score:** 5.3 (Medium)

**Issue:**
```python
except Exception as e:
    logger.error(f"OAuth error: {e}")
    raise HTTPException(status_code=500, detail=str(e))  # Exposes internal details
```

**Impact:**
- Stack traces reveal file paths, dependencies
- Error messages expose database structure
- Helps attackers understand system architecture

**Recommendation:**
```python
except Exception as e:
    logger.error(f"OAuth error: {e}")
    # Generic message for users, detailed log for admins
    raise HTTPException(status_code=500, detail="Authentication failed. Please try again.")
```

---

### 8. 🟠 HIGH: No Rate Limiting
**Location:** All API endpoints  
**Risk:** Denial of Service, Brute Force  
**CVSS Score:** 6.5 (Medium)

**Issue:**
No rate limiting on any endpoints allows:
- Brute force attacks (if auth is added)
- API abuse
- Resource exhaustion
- Excessive external API calls (cost)

**Recommendation:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/sync")
@limiter.limit("5/minute")
def sync_portfolio(request: Request):
    # Limited to 5 requests per minute
```

---

## Medium Priority Issues

### 9. 🟡 MEDIUM: Open Redirect Vulnerability
**Location:** `backend/main.py:465` (Zerodha callback)  
**Risk:** Phishing  
**CVSS Score:** 5.4 (Medium)

**Issue:**
```python
return RedirectResponse(url="/?zerodha=connected")
```

While currently hardcoded, if this becomes parameterized:
```python
# DANGEROUS (example of what to avoid):
redirect_url = request.query_params.get('redirect')
return RedirectResponse(url=redirect_url)  # Open redirect!
```

**Recommendation:**
```python
# Whitelist allowed redirects
ALLOWED_REDIRECTS = ['/', '/dashboard', '/settings']

def safe_redirect(url: str):
    if url not in ALLOWED_REDIRECTS:
        url = '/'
    return RedirectResponse(url=url)
```

---

### 10. 🟡 MEDIUM: Dependency Vulnerabilities
**Location:** Python packages  
**Risk:** Various  
**CVSS Score:** Variable

**Current Versions:**
- `requests==2.31.0` (known CVEs)
- FastAPI, SQLModel, Pydantic (check for updates)

**Recommendation:**
```bash
# Regular security audits
pip install safety
safety check

# Update dependencies
pip install --upgrade requests fastapi sqlmodel

# Pin versions in requirements.txt
```

---

### 11. 🟡 MEDIUM: No Input Validation on Config Updates
**Location:** `backend/main.py:242` (PUT /api/config)  
**Risk:** Data Integrity  
**CVSS Score:** 4.3 (Medium)

**Issue:**
```python
@app.put("/api/config/{key}")
def update_config(key: str, value: str):
    # No validation on key or value!
    config.value = value
```

**Impact:**
- Malformed API keys stored
- Injection of malicious values
- System misconfiguration

**Recommendation:**
```python
from pydantic import validator

class ConfigUpdate(BaseModel):
    key: str
    value: str
    
    @validator('key')
    def validate_key(cls, v):
        allowed_keys = ['perplexity_api_key', 'zerodha_api_key', etc]
        if v not in allowed_keys:
            raise ValueError('Invalid config key')
        return v
    
    @validator('value')
    def validate_value(cls, v, values):
        # Validate format based on key
        if values.get('key') == 'perplexity_api_key':
            if not v.startswith('pplx-'):
                raise ValueError('Invalid Perplexity API key format')
        return v
```

---

### 12. 🟡 MEDIUM: Insecure Database File Permissions
**Location:** `portfolio.db`  
**Risk:** Unauthorized Access  
**CVSS Score:** 5.5 (Medium)

**Issue:**
SQLite database created with default permissions (readable by others on system).

**Recommendation:**
```python
import os
import stat

# Set restrictive permissions on database file
os.chmod('portfolio.db', stat.S_IRUSR | stat.S_IWUSR)  # 0600 (owner only)
```

---

## Low Priority Issues

### 13. 🟢 LOW: Missing Security Headers
**Location:** HTTP responses  
**Risk:** Various browser-based attacks  

**Missing Headers:**
- `X-Frame-Options` (clickjacking protection)
- `X-Content-Type-Options` (MIME sniffing)
- `Content-Security-Policy` (XSS additional protection)
- `Strict-Transport-Security` (force HTTPS)

**Recommendation:**
```python
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

### 14. 🟢 LOW: No Logging of Security Events
**Location:** Throughout application  
**Risk:** Lack of audit trail  

**Recommendation:**
```python
# Log security-relevant events
logger.warning(f"Failed login attempt from {request.client.host}")
logger.info(f"Config changed: {key} by user {user_id}")
logger.critical(f"Multiple failed attempts from {ip}")
```

---

### 15. 🟢 LOW: Session Management
**Location:** Not implemented  

**Recommendation:**
For production, implement:
- Session timeout (15-30 minutes)
- Secure session storage (Redis)
- Session invalidation on logout
- HTTPS-only session cookies

---

## Security Checklist for Production

### Immediate Actions (Pre-Production)
- [ ] Encrypt sensitive data in database
- [ ] Implement authentication/authorization
- [ ] Sanitize all user inputs (frontend)
- [ ] Enable HTTPS/TLS
- [ ] Add CSRF protection
- [ ] Generic error messages only
- [ ] Rate limiting on all endpoints
- [ ] Input validation on all forms

### Short-term (Within 1 month)
- [ ] Security headers middleware
- [ ] Dependency vulnerability scanning
- [ ] Security event logging
- [ ] Database file permissions
- [ ] Open redirect prevention
- [ ] Session management

### Long-term (Ongoing)
- [ ] Regular security audits
- [ ] Penetration testing
- [ ] Dependency updates
- [ ] Security monitoring
- [ ] Incident response plan

---

## Compliance Considerations

### Financial Data Regulations
- **PCI DSS:** If storing payment cards (not currently)
- **SOC 2:** For service providers
- **Data Residency:** Consider data location requirements

### Privacy Regulations
- **GDPR:** If serving EU users
- **CCPA:** If serving California users
- **Data retention policies**
- **Right to deletion**

---

## Security Tools Recommendations

```bash
# Install security tools
pip install bandit safety

# Static analysis
bandit -r backend/

# Dependency audit
safety check

# Frontend security
npm install -g snyk
snyk test
```

---

## Conclusion

The Stock Dashboard application has significant security gaps typical of development/demo applications. **It is NOT production-ready in its current state.**

**Critical Action Items:**
1. **Encrypt all sensitive data** - Highest priority
2. **Implement authentication** - Required before any external access
3. **Fix XSS vulnerabilities** - Critical for user safety
4. **Enable HTTPS** - Required for credential transmission
5. **Add CSRF protection** - Prevent unauthorized actions

**Estimated Remediation Time:** 2-3 weeks for critical items, 1-2 months for full hardening.

**Risk Assessment:**
- **Current State:** Suitable for local demo/development only
- **After Critical Fixes:** Suitable for internal use on trusted network
- **After All Fixes:** Suitable for production deployment

---

**Prepared by:** Security Assessment Tool  
**Next Review:** After remediation or within 3 months  
**Contact:** Review findings with security team before production deployment

---

## Appendix: Code Examples

### Secure Configuration Example

```python
# backend/security.py
from cryptography.fernet import Fernet
import os

class SecureConfigManager:
    def __init__(self):
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable required")
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, value: str) -> bytes:
        return self.cipher.encrypt(value.encode())
    
    def decrypt(self, encrypted: bytes) -> str:
        return self.cipher.decrypt(encrypted).decode()
```

### Authentication Example

```python
# backend/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

# Usage in endpoints
@app.get("/api/stocks")
def get_stocks(current_user: str = Depends(get_current_user)):
    # Now requires valid JWT token
    pass
```

---

**END OF SECURITY ASSESSMENT REPORT**
