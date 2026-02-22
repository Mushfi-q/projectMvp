from app.database import SessionLocal
from app.models.academic import Department, Batch, Semester, Subject, Faculty, SubjectOffering, Student
from app.models.user import User

db = SessionLocal()

# Department
dept = Department(name="AI & ML")
db.add(dept)
db.commit()
db.refresh(dept)

# Batch
batch = Batch(department_id=dept.id, start_year=2024, end_year=2027)
db.add(batch)
db.commit()
db.refresh(batch)

# Semester
sem = Semester(semester_number=1, batch_id=batch.id, academic_year="2025-2026")
db.add(sem)
db.commit()
db.refresh(sem)

# Subject
sub = Subject(subject_name="IoT", subject_code="IOT101", department_id=dept.id)
db.add(sub)
db.commit()
db.refresh(sub)

from app.core.security import hash_password

# ... existing imports ...

# Faculty User
faculty_user = User(name="Faculty1", email="fac1@gmail.com", password_hash=hash_password("123"), role="faculty")
db.add(faculty_user)
db.commit()
db.refresh(faculty_user)

# Faculty
faculty = Faculty(user_id=faculty_user.id, department_id=dept.id, designation="Professor")
db.add(faculty)
db.commit()
db.refresh(faculty)

# Subject Offering
offering = SubjectOffering(subject_id=sub.id, semester_id=sem.id, faculty_id=faculty.id)
db.add(offering)
db.commit()
db.refresh(offering)

print("SubjectOffering ID:", offering.id)

db.close()
