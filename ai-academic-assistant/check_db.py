import os
import sys

# add parent directory to path so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from sqlalchemy.orm import Session
from app.database import engine
from app.models.academic import Department, Batch, Semester

session = Session(engine)

depts = session.query(Department).all()
batches = session.query(Batch).all()
sems = session.query(Semester).all()

print("Departments:", [{"id": d.id, "name": d.name} for d in depts])
print("Batches:", [{"id": b.id, "dept_id": b.department_id, "start": b.start_year} for b in batches])
print("Semesters:", [{"id": s.id, "batch_id": s.batch_id, "number": s.semester_number} for s in sems])
