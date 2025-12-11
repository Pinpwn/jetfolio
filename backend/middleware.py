"""
Security Middleware - HTTP Security Headers and Rate Limiting

Adds security headers to all HTTP responses to protect against:
- Clickjacking (X-Frame-Options)
- MIME sniffing (X-Content-Type-Options)
- XSS (X-XSS-Protection, Content-Security-Policy)

For production, also implement:
- HTTPS enforcement (Strict-Transport-Security)
- Rate limiting to prevent abuse
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security-related HTTP headers to all responses.
    
    Headers Added:
        X-Frame-Options: DENY - Prevents clickjacking
        X-Content-Type-Options: nosniff - Prevents MIME sniffing
        X-XSS-Protection: 1; mode=block - Browser XSS filter
        Content-Security-Policy: Restricts resource loading
    
    Usage:
        app.add_middleware(SecurityHeadersMiddleware)
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request and add security headers to response."""
        response: Response = await call_next(request)
        
        # Prevent clickjacking - don't allow framing
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable browser XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy - restrict resource loading
        # Adjust CSP based on your needs (e.g., if using external CDNs)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:;"
        )
        
        # For production over HTTPS, add HSTS
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
