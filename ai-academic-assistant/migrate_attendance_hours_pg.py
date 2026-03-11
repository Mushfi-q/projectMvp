from sqlalchemy import text
from app.database import engine

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text('ALTER TABLE attendance ADD COLUMN hours INTEGER DEFAULT 1;'))
            conn.commit()
            print("Successfully added hours column to Postgres DB.")
        except Exception as e:
            print(f"Migration error (might already exist): {e}")

if __name__ == "__main__":
    migrate()
