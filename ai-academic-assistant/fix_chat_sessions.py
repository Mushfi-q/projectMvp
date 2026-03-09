"""
Fix chat_sessions table: add ALL missing columns that the SQLAlchemy model expects.
DB has: [id, user_id, started_at]
Model expects: [id, student_id, subject_offering_id, created_at]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'chat_sessions'"
    ))
    existing = [r[0] for r in result]
    print(f"Existing columns: {existing}")

    migrations = {
        'student_id': "ALTER TABLE chat_sessions ADD COLUMN student_id INTEGER REFERENCES students(id)",
        'subject_offering_id': "ALTER TABLE chat_sessions ADD COLUMN subject_offering_id INTEGER REFERENCES subject_offerings(id)",
        'created_at': "ALTER TABLE chat_sessions ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW()",
    }

    for col, sql in migrations.items():
        if col not in existing:
            print(f"Adding {col}...")
            conn.execute(text(sql))
            conn.commit()
            print(f"  ✓ {col} added")
        else:
            print(f"  {col} already exists")

    print("\nDone! Final columns:")
    result2 = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'chat_sessions'"
    ))
    print([r[0] for r in result2])
