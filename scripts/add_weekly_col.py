from sqlmodel import Session, text
from backend.database import engine

def migrate():
    with Session(engine) as session:
        try:
            print("Adding weekly_change_percentage column to Stock table...")
            session.exec(text("ALTER TABLE stock ADD COLUMN weekly_change_percentage FLOAT"))
            session.commit()
            print("Migration successful.")
        except Exception as e:
            print(f"Migration failed (maybe column exists?): {e}")

if __name__ == "__main__":
    migrate()
