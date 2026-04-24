"""
Database Setup Script
---------------------
Creates all tables in the fresh Railway PostgreSQL database
and seeds an admin user so the app is functional again.

Run from the ai-academic-assistant directory:
    python setup_db.py
"""

import sys
import os

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(__file__))

from app.config import DATABASE_URL
from app.database import engine, Base

# Import ALL models so Base.metadata knows about every table
from app.models import user, academic, assignment, attendance, chat, reminder

from app.core.security import hash_password
from sqlalchemy.orm import Session

def main():
    print(f"Connecting to database...")
    print(f"  URL: {DATABASE_URL[:40]}...")
    
    # 1. Create all tables
    print("\n[1/3] Creating all tables...")
    Base.metadata.create_all(bind=engine)
    
    # List the tables that were created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"  OK - Tables created: {', '.join(tables)}")
    
    # 2. Seed the admin user
    print("\n[2/3] Seeding admin user...")
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        from app.models.user import User
        
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.role == "admin").first()
        if existing_admin:
            print(f"  INFO - Admin user already exists: {existing_admin.email}")
        else:
            admin_user = User(
                name="Admin",
                email="admin@admin.com",
                password_hash=hash_password("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"  OK - Admin user created!")
            print(f"    Email:    admin@admin.com")
            print(f"    Password: admin123")
        
        # 3. Summary
        print("\n[3/3] Database summary:")
        user_count = db.query(User).count()
        print(f"  Users:        {user_count}")
        
        from app.models.academic import Department, Batch, Semester
        dept_count = db.query(Department).count()
        batch_count = db.query(Batch).count()
        sem_count = db.query(Semester).count()
        print(f"  Departments:  {dept_count}")
        print(f"  Batches:      {batch_count}")
        print(f"  Semesters:    {sem_count}")
        
        print("\nDONE - Database is ready! You can now run:")
        print("   uvicorn app.main:app --reload")
        
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
