"""
Security Utilities - Encryption and Authentication

This module provides security utilities for the Stock Dashboard:
- API key encryption/decryption
- Input sanitization helpers
- Security middleware

PRODUCTION SETUP REQUIRED:
    1. Set ENCRYPTION_KEY environment variable:
       export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    2. For JWT auth (future):
       export JWT_SECRET_KEY=$(openssl rand -hex 32)
"""

from cryptography.fernet import Fernet
import os
from typing import Optional
import html


class SecureConfigManager:
    """
    Manages encryption and decryption of sensitive configuration data.
    
    Usage:
        manager = SecureConfigManager()
        encrypted = manager.encrypt("my-api-key")
        decrypted = manager.decrypt(encrypted)
    
    Environment Variables:
        ENCRYPTION_KEY: Fernet encryption key (base64-encoded)
    """
    
    def __init__(self):
        """Initialize with encryption key from environment."""
        key = os.getenv('ENCRYPTION_KEY')
        
        if not key:
            # For development only - generate a temporary key
            # WARNING: This means data won't persist across restarts!
            import warnings
            warnings.warn(
                "ENCRYPTION_KEY not set. Using temporary key. "
                "Data will not be decryptable after restart. "
                "Set ENCRYPTION_KEY in production!",
                RuntimeWarning
            )
            key = Fernet.generate_key().decode()
            os.environ['ENCRYPTION_KEY'] = key
        
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, value: str) -> bytes:
        """
        Encrypt a string value.
        
        Args:
            value: Plaintext string to encrypt
            
        Returns:
            Encrypted bytes
        """
        return self.cipher.encrypt(value.encode())
    
    def decrypt(self, encrypted: bytes) -> str:
        """
        Decrypt encrypted bytes to string.
        
        Args:
            encrypted: Encrypted bytes
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        return self.cipher.decrypt(encrypted).decode()


def sanitize_html(text: str) -> str:
    """
    Sanitize user input to prevent XSS attacks.
    
    Escapes HTML special characters to prevent script injection.
    Use this for any user-generated content before displaying.
    
    Args:
        text: Potentially unsafe user input
        
    Returns:
        HTML-escaped safe string
        
    Example:
        >>> sanitize_html("<script>alert('xss')</script>")
        "&lt;script&gt;alert('xss')&lt;/script&gt;"
    """
    if not text:
        return ""
    return html.escape(str(text))


def validate_api_key_format(key: str, key_type: str) -> bool:
    """
    Validate API key format before storing.
    
    Args:
        key: API key to validate
        key_type: Type of key ('perplexity', 'zerodha_api_key', etc.)
        
    Returns:
        True if format is valid
        
    Raises:
        ValueError: If format is invalid
    """
    if not key or not isinstance(key, str):
        raise ValueError("API key must be a non-empty string")
    
    # Format validation by key type
    if key_type == "perplexity_api_key":
        if not key.startswith("pplx-"):
            raise ValueError("Perplexity API key must start with 'pplx-'")
        if len(key) < 20:
            raise ValueError("Perplexity API key too short")
    
    elif key_type == "zerodha_api_key":
        if len(key) < 10:
            raise ValueError("Zerodha API key too short")
    
    return True


# Global instance for use across application
_secure_config = None

def get_secure_config() -> SecureConfigManager:
    """
    Get singleton instance of SecureConfigManager.
    
    Returns:
        Shared SecureConfigManager instance
    """
    global _secure_config
    if _secure_config is None:
        _secure_config = SecureConfigManager()
    return _secure_config
