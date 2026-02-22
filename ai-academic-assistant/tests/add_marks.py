from app.database import SessionLocal
from app.models.assignment import InternalMark
from app.models.academic import Student

db = SessionLocal()

# Get the student (assuming there is one from enroll_student.py)
student = db.query(Student).first()

if not student:
    print("No student found. Run enroll_student.py first.")
else:
    # Add low marks for SubjectOffering 1
    mark = InternalMark(
        subject_offering_id=1,
        student_id=student.id,
        marks_obtained=40,
        max_marks=100
    )

    db.add(mark)
    db.commit()
    print(f"Marks added for Student {student.id}: 40/100")

db.close()
