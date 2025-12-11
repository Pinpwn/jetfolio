import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

#Configure logger
logger = logging.getLogger("stock_dashboard")
logger.setLevel(logging.DEBUG)

# File handler with rotation (10MB max, keep 5 backups)
file_handler = RotatingFileHandler(
    LOGS_DIR / "app.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)

# Console handler (optional, for development)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Prevent propagation to root logger
logger.propagate = False

def get_recent_logs(lines=100):
    """Read the last N lines from the log file."""
    log_file = LOGS_DIR / "app.log"
    if not log_file.exists():
        return []
    
    with open(log_file, 'r') as f:
        all_lines = f.readlines()
        return all_lines[-lines:] if len(all_lines) > lines else all_lines
