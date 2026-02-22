from app.database import SessionLocal
from app.models.user import User
from app.models.academic import Student, Enrollment

db = SessionLocal()

# Check if user exists first to avoid errors
student_email = "student@gmail.com"
student_user = db.query(User).filter(User.email == student_email).first()

if not student_user:
    print(f"User {student_email} not found. Creating...")
    from app.core.security import hash_password
    student_user = User(
        name="Student User",
        email=student_email,
        password_hash=hash_password("123"), # Default password for testing
        role="student"
    )
    db.add(student_user)
    db.commit()
    db.refresh(student_user)

# Check if student record already exists
existing_student = db.query(Student).filter(Student.user_id == student_user.id).first()
if existing_student:
    print("Student record already exists.")
    student = existing_student
else:
    student = Student(
        user_id=student_user.id,
        register_number="REG001",
        batch_id=1,
        section="A",
        current_semester_id=1
    )
    db.add(student)
    db.commit()
    db.refresh(student)

# Check if enrollment already exists
existing_enrollment = db.query(Enrollment).filter(
    Enrollment.student_id == student.id,
    Enrollment.subject_offering_id == 1
).first()

if existing_enrollment:
    print("Student already enrolled.")
else:
    enrollment = Enrollment(
        student_id=student.id,
        subject_offering_id=1
    )
    db.add(enrollment)
    db.commit()
    print("Student enrolled successfully")

db.close()
