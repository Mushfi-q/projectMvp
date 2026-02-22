from app.database import SessionLocal
from app.models.assignment import Assignment
from app.models.academic import SubjectOffering
from datetime import datetime, timedelta

db = SessionLocal()

# Assign to SubjectOffering ID 1
# Due in 2 days (Urgent)
assignment1 = Assignment(
    subject_offering_id=1,
    title="IoT Architecture Diagram",
    description="Draw the 4-layer architecture diagram of IoT.",
    deadline=datetime.utcnow() + timedelta(days=2)
)

db.add(assignment1)

# Due in 10 days (Upcoming)
assignment2 = Assignment(
    subject_offering_id=1,
    title="Sensor Data Report",
    description="Submit report on different types of sensors.",
    deadline=datetime.utcnow() + timedelta(days=10)
)

db.add(assignment2)

db.commit()
print("Assignments added successfully")

db.close()
