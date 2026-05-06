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
import html
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models import Config


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
        
        try:
            self.cipher = Fernet(key.encode())
        except Exception as e:
            # Handle invalid key
            import warnings
            warnings.warn(f"Invalid ENCRYPTION_KEY: {e}. Generating a new one for this session.")
            new_key = Fernet.generate_key().decode()
            os.environ['ENCRYPTION_KEY'] = new_key
            self.cipher = Fernet(new_key.encode())
    
    def encrypt(self, value: str) -> str:
        """
        Encrypt a string value.
        
        Args:
            value: Plaintext string to encrypt
            
        Returns:
            Encrypted value as a base64-encoded string
        """
        if not value:
            return ""
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted_value: str) -> str:
        """
        Decrypt encrypted string to plaintext.
        
        Args:
            encrypted_value: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        if not encrypted_value:
            return ""
        return self.cipher.decrypt(encrypted_value.encode()).decode()

    def get_value(self, config_item: "Config") -> str:
        """
        Safely retrieve the value from a Config object, decrypting if necessary.
        
        Args:
            config_item: Config database model object
            
        Returns:
            Decrypted (if needed) plaintext value
        """
        if not config_item:
            return ""
            
        if config_item.is_encrypted:
            try:
                return self.decrypt(config_item.value)
            except Exception as e:
                import logging
                logging.error(f"Failed to decrypt config key {config_item.key}: {e}")
                return config_item.value  # Fallback to raw if decryption fails (might be unencrypted)
        
        return config_item.value


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


def get_api_key(session, key_name: str) -> Optional[str]:
    """
    Retrieve an API key from Environment Variables or the Config table.
    
    Args:
        session: Database session
        key_name: Name of the key (e.g. 'perplexity_api_key')
        
    Returns:
        The API key string or None if not found
    """
    import os
    
    # 1. Check environment variable (convert to uppercase, e.g. PERPLEXITY_API_KEY)
    env_name = key_name.upper()
    env_val = os.getenv(env_name)
    if env_val:
        return env_val
        
    # 2. Fallback to Database Config
    from backend.models import Config
    config = session.get(Config, key_name)
    return config.value if config else None


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
