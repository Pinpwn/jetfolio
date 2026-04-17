import sys
import os
import time
# Add project root to path
sys.path.append(os.getcwd())

from backend.database import get_session, engine
from sqlmodel import Session, select
from backend.models import NewsArticle
from backend.services.analysis_manager import AnalysisManager
from backend.logger import logger

def debug_analysis():
    print("Checking for pending articles...")
    with Session(engine) as session:
        pending = session.exec(select(NewsArticle).where(NewsArticle.processing_status == "pending")).all()
        print(f"Found {len(pending)} pending articles.")
        
        total = session.exec(select(NewsArticle)).all()
        print(f"Total articles in DB: {len(total)}")
        
        if pending:
            print("First pending article:", pending[0].title, pending[0].url)
            
    print("\nTriggering AnalysisManager...")
    manager = AnalysisManager()
    # Run synchronously for debug
    manager.process_pending_articles()
    print("AnalysisManager run complete.")

if __name__ == "__main__":
    debug_analysis()
