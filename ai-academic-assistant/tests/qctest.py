from app.database import SessionLocal
from app.models.assignment import Assignment

db = SessionLocal()
assignments = db.query(Assignment).all()
if not assignments:
    print("No assignments found.")
else:
    for a in assignments:
        print(f"Title: {a.title}, Deadline: {a.deadline}")
db.close()