from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.core.dependencies import get_db

from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Auth"])

class StudentRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str
    department_id: int
    batch_id: int
    semester_number: int

@router.get("/departments", summary="Get all available departments")
def get_departments(db: Session = Depends(get_db)):
    from app.models.academic import Department
    depts = db.query(Department).all()
    return {
        "success": True, 
        "data": [{"id": d.id, "name": d.name} for d in depts]
    }

@router.get("/departments/{department_id}/batches", summary="Get all batches for a department")
def get_batches(department_id: int, db: Session = Depends(get_db)):
    from app.models.academic import Batch
    batches = db.query(Batch).filter(Batch.department_id == department_id).all()
    return {
        "success": True,
        "data": [{"id": b.id, "start_year": b.start_year, "end_year": b.end_year} for b in batches]
    }

@router.post("/register", summary="Register a new Student and autolink academic profile")
def register(data: StudentRegisterRequest, db: Session = Depends(get_db)):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
        
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    from app.models.academic import Department, Batch, Semester, Student, Enrollment, SubjectOffering

    # 1. Validate Academic existence
    dept = db.query(Department).filter(Department.id == data.department_id).first()
    if not dept:
        raise HTTPException(status_code=400, detail="Invalid Department")
        
    # Validate the Explicitly Provided Batch
    batch = db.query(Batch).filter(Batch.id == data.batch_id, Batch.department_id == dept.id).first()
    if not batch:
        raise HTTPException(status_code=400, detail="Invalid batch selected for this department")
        
    semester = db.query(Semester).filter(Semester.batch_id == batch.id, Semester.semester_number == data.semester_number).first()
    if not semester:
        raise HTTPException(status_code=400, detail=f"Semester {data.semester_number} not established for this batch yet.")

    # 2. Create User (Role locked to Student)
    new_user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role="student"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 3. Create Student Profile
    student = Student(
        user_id=new_user.id,
        batch_id=batch.id,
        current_semester_id=semester.id,
        register_number=f"REG-{new_user.id}00" # Automatic mockup ID
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    # 4. Auto Enroll in Subjects mapped to this semester
    offerings = db.query(SubjectOffering).filter(SubjectOffering.semester_id == semester.id).all()
    for off in offerings:
        enroll = Enrollment(
            student_id=student.id,
            subject_offering_id=off.id
        )
        db.add(enroll)
    db.commit()

    return {
        "success": True,
        "data": "Account and Academic profile created successfully!"
    }


class FacultyRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str
    department_id: int
    designation: str = "Assistant Professor"

@router.post("/register-faculty", summary="Register a new Faculty and autolink department profile")
def register_faculty(data: FacultyRegisterRequest, db: Session = Depends(get_db)):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    from app.models.academic import Department, Faculty

    dept = db.query(Department).filter(Department.id == data.department_id).first()
    if not dept:
        raise HTTPException(status_code=400, detail="Invalid Department")

    # Create User (Role locked to Faculty)
    new_user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role="faculty"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create Faculty Profile
    faculty = Faculty(
        user_id=new_user.id,
        department_id=dept.id,
        designation=data.designation
    )
    db.add(faculty)
    db.commit()

    return {
        "success": True,
        "data": "Faculty account and department profile created successfully!"
    }

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role
        }
    }
