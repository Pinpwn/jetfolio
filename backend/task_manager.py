"""
Task Manager - Background Task Status Tracking

Tracks the status and completion times of background tasks to provide
visibility into async operations like data sync and news refresh.
"""

from datetime import datetime
from typing import Optional


class TaskManager:
    """
    Simple in-memory task status tracker for background operations.
    
    Tracks running state and last completion time for:
    - sync: Data synchronization from brokers and price fetching
    - refresh: News scraping and event detection
    """
    
    def __init__(self):
        """Initialize task manager with empty status."""
        self.status = {
            "sync_running": False,
            "sync_last_completed": None,
            "refresh_running": False,
            "refresh_last_completed": None,
        }
    
    def start_sync(self):
        """Mark sync task as running."""
        self.status["sync_running"] = True
    
    def complete_sync(self):
        """Mark sync task as completed."""
        self.status["sync_running"] = False
        self.status["sync_last_completed"] = datetime.utcnow().isoformat()
    
    def start_refresh(self):
        """Mark refresh task as running."""
        self.status["refresh_running"] = True
    
    def complete_refresh(self):
        """Mark refresh task as completed."""
        self.status["refresh_running"] = False
        self.status["refresh_last_completed"] = datetime.utcnow().isoformat()
    
    def get_status(self) -> dict:
        """
        Get current status of all background tasks.
        
        Returns:
            Dictionary with running states and last completion times
        """
        return self.status.copy()


# Global singleton instance
task_manager = TaskManager()
