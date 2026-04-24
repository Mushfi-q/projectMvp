import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.services.rag_service import build_index
from app.models.assignment import Document
from app.models.academic import Student, Semester, StudentSemesterHistory
from app.services.ai_service import get_student_performance_summary

UPLOAD_PATH = "uploaded_pdfs"
os.makedirs(UPLOAD_PATH, exist_ok=True)

router = APIRouter(prefix="/admin", tags=["Admin"])
from pydantic import BaseModel

class DepartmentCreate(BaseModel):
    name: str

class BatchCreate(BaseModel):
    department_id: int
    start_year: int
    end_year: int

class SemesterCreate(BaseModel):
    batch_id: int
    semester_number: int
    academic_year: str
    is_active: int = 1

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str

class StudentCreate(BaseModel):
    user_id: int
    register_number: str
    batch_id: int
    section: str
    current_semester_id: int

class FacultyCreate(BaseModel):
    name: str
    email: str
    password: str
    department_id: int
    designation: str

class GenericAdminResponse(BaseModel):
    success: bool
    data: str

# -------- Structural Setup --------

@router.post("/department", response_model=GenericAdminResponse, summary="Create a new Department")
def create_department(data: DepartmentCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Department
    dept = Department(name=data.name)
    db.add(dept)
    db.commit()
    return {"success": True, "data": "Department created successfully"}

@router.post("/batch", response_model=GenericAdminResponse, summary="Create a new Batch")
def create_batch(data: BatchCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Batch
    batch = Batch(**data.model_dump())
    db.add(batch)
    db.commit()
    return {"success": True, "data": "Batch created successfully"}

@router.post("/semester", response_model=GenericAdminResponse, summary="Create a new Semester")
def create_semester(data: SemesterCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Semester
    semester = Semester(**data.model_dump())
    db.add(semester)
    db.commit()
    return {"success": True, "data": "Semester created successfully"}

# -------- User Creation --------

from app.core.security import hash_password
from app.models.user import User

@router.post("/student", response_model=GenericAdminResponse, summary="Create a new Student Profile")
def create_student(data: StudentCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    student = Student(**data.model_dump())
    db.add(student)
    db.commit()
    return {"success": True, "data": "Student profile linked successfully"}

@router.post("/faculty", response_model=GenericAdminResponse, summary="Create a new Faculty Profile")
def create_faculty(data: FacultyCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    
    # 1. Check if user already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # 2. Create User account
    new_user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role="faculty"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 3. Create Faculty profile linked to User
    from app.models.academic import Faculty
    faculty = Faculty(
        user_id=new_user.id,
        department_id=data.department_id,
        designation=data.designation
    )
    db.add(faculty)
    db.commit()
    
    return {"success": True, "data": f"Faculty profile created for {data.name}"}


# -------- Listing Endpoints --------

@router.get("/departments", summary="List all Departments")
def list_departments(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Department
    depts = db.query(Department).all()
    return {"success": True, "data": [{"id": d.id, "name": d.name} for d in depts]}

@router.get("/batches", summary="List all Batches")
def list_batches(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Batch, Department
    batches = db.query(Batch).all()
    result = []
    for b in batches:
        dept = db.query(Department).filter(Department.id == b.department_id).first()
        result.append({
            "id": b.id,
            "department": dept.name if dept else "Unknown",
            "start_year": b.start_year,
            "end_year": b.end_year
        })
    return {"success": True, "data": result}

@router.get("/students", summary="List all Students")
def list_students(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Batch
    students = db.query(Student).all()
    result = []
    for s in students:
        user = db.query(User).filter(User.id == s.user_id).first()
        batch = db.query(Batch).filter(Batch.id == s.batch_id).first()
        sem = db.query(Semester).filter(Semester.id == s.current_semester_id).first()
        result.append({
            "id": s.id,
            "name": user.name if user else "Unknown",
            "email": user.email if user else "Unknown",
            "register_number": s.register_number or "N/A",
            "batch": f"{batch.start_year}-{batch.end_year}" if batch else "N/A",
            "semester": sem.semester_number if sem else "N/A"
        })
    return {"success": True, "data": result}

@router.get("/faculties", summary="List all Faculty")
def list_faculties(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Faculty, Department
    faculties = db.query(Faculty).all()
    result = []
    for f in faculties:
        user = db.query(User).filter(User.id == f.user_id).first()
        dept = db.query(Department).filter(Department.id == f.department_id).first()
        result.append({
            "id": f.id,
            "name": user.name if user else "Unknown",
            "email": user.email if user else "Unknown",
            "department": dept.name if dept else "Unknown",
            "designation": f.designation or "N/A"
        })
    return {"success": True, "data": result}

@router.get("/semesters", summary="List all Semesters")
def list_semesters(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Batch
    semesters = db.query(Semester).all()
    result = []
    for s in semesters:
        batch = db.query(Batch).filter(Batch.id == s.batch_id).first()
        result.append({
            "id": s.id,
            "batch": f"{batch.start_year}-{batch.end_year}" if batch else "N/A",
            "batch_id": s.batch_id,
            "semester_number": s.semester_number,
            "academic_year": s.academic_year,
            "is_active": s.is_active
        })
    return {"success": True, "data": result}

@router.get("/enrollments", summary="List all Enrollments")
def list_enrollments(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Enrollment, SubjectOffering, Subject
    enrollments = db.query(Enrollment).all()
    result = []
    for e in enrollments:
        student = db.query(Student).filter(Student.id == e.student_id).first()
        user = db.query(User).filter(User.id == student.user_id).first() if student else None
        offering = db.query(SubjectOffering).filter(SubjectOffering.id == e.subject_offering_id).first()
        subj = db.query(Subject).filter(Subject.id == offering.subject_id).first() if offering else None
        result.append({
            "id": e.id,
            "student": user.name if user else "Unknown",
            "student_id": e.student_id,
            "subject": subj.subject_name if subj else "Unknown",
            "subject_code": subj.subject_code if subj else "N/A",
            "offering_id": e.subject_offering_id,
            "date": str(e.enrollment_date)[:10] if e.enrollment_date else "N/A"
        })
    return {"success": True, "data": result}


# -------- Subject Management --------

class SubjectCreate(BaseModel):
    subject_name: str
    subject_code: str
    department_id: int

class SubjectOfferingCreate(BaseModel):
    subject_id: int
    semester_id: int
    faculty_id: int

@router.post("/subject", response_model=GenericAdminResponse, summary="Create a new Subject")
def create_subject(data: SubjectCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Subject
    subject = Subject(**data.model_dump())
    db.add(subject)
    db.commit()
    return {"success": True, "data": "Subject created successfully"}

@router.post("/subject-offering", response_model=GenericAdminResponse, summary="Create a Subject Offering")
def create_subject_offering(data: SubjectOfferingCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import SubjectOffering, Subject, Semester, Faculty
    
    # Verify entities exist
    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
    semester = db.query(Semester).filter(Semester.id == data.semester_id).first()
    faculty = db.query(Faculty).filter(Faculty.id == data.faculty_id).first()
    
    if not subject: raise HTTPException(status_code=404, detail="Subject not found")
    if not semester: raise HTTPException(status_code=404, detail="Semester not found")
    if not faculty: raise HTTPException(status_code=404, detail="Faculty not found")

    # Check if this exact mapping already exists
    existing = db.query(SubjectOffering).filter(
        SubjectOffering.subject_id == data.subject_id,
        SubjectOffering.semester_id == data.semester_id,
        SubjectOffering.faculty_id == data.faculty_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="This subject is already mapped to this faculty for this semester")

    offering = SubjectOffering(
        subject_id=data.subject_id,
        semester_id=data.semester_id,
        faculty_id=data.faculty_id 
    )
    db.add(offering)
    db.commit()
    
    return {"success": True, "data": "Subject mapped successfully"}

@router.get("/subjects", summary="List all Subjects")
def list_subjects(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import Subject, Department
    subjects = db.query(Subject).all()
    result = []
    for s in subjects:
        dept = db.query(Department).filter(Department.id == s.department_id).first()
        result.append({
            "id": s.id,
            "name": s.subject_name,
            "code": s.subject_code,
            "department": dept.name if dept else "Unknown"
        })
    return {"success": True, "data": result}

@router.get("/subject-offerings", summary="List all Subject Offerings")
def list_subject_offerings(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    from app.models.academic import SubjectOffering, Subject, Faculty
    offerings = db.query(SubjectOffering).all()
    result = []
    for o in offerings:
        subj = db.query(Subject).filter(Subject.id == o.subject_id).first()
        sem = db.query(Semester).filter(Semester.id == o.semester_id).first()
        fac_record = db.query(Faculty).filter(Faculty.id == o.faculty_id).first()
        fac_user = db.query(User).filter(User.id == fac_record.user_id).first() if fac_record else None
        result.append({
            "id": o.id,
            "subject": subj.subject_name if subj else "Unknown",
            "code": subj.subject_code if subj else "N/A",
            "semester": sem.semester_number if sem else "N/A",
            "faculty": fac_user.name if fac_user else "Unassigned"
        })
    return {"success": True, "data": result}


# -------- Delete Endpoints (Cascade) --------

from sqlalchemy.exc import IntegrityError as SAIntegrityError
from app.models.academic import (
    Department, Batch, Semester, Subject, SubjectOffering, Enrollment, Faculty, StudentSemesterHistory
)
from app.models.assignment import Assignment, Submission, Document, DocumentChunk
from app.models.attendance import Attendance
from app.models.reminder import Reminder


def _count_dependents(db, entity, item_id):
    """Count all dependent records that would be cascade-deleted."""
    counts = {}

    if entity == "department":
        batches = db.query(Batch).filter(Batch.department_id == item_id).all()
        batch_ids = [b.id for b in batches]
        counts["Batches"] = len(batches)
        # children of batches
        semesters = db.query(Semester).filter(Semester.batch_id.in_(batch_ids)).all() if batch_ids else []
        sem_ids = [s.id for s in semesters]
        counts["Semesters"] = len(semesters)
        students = db.query(Student).filter(Student.batch_id.in_(batch_ids)).all() if batch_ids else []
        student_ids = [s.id for s in students]
        counts["Students"] = len(students)
        # subject offerings from semesters
        so = db.query(SubjectOffering).filter(SubjectOffering.semester_id.in_(sem_ids)).all() if sem_ids else []
        so_ids = [o.id for o in so]
        counts["Subject Offerings"] = len(so)
        # enrollments, assignments, etc from subject offerings
        enroll = db.query(Enrollment).filter(Enrollment.subject_offering_id.in_(so_ids)).all() if so_ids else []
        enroll_ids = [e.id for e in enroll]
        counts["Enrollments"] = len(enroll)
        counts["Attendance Records"] = db.query(Attendance).filter(Attendance.enrollment_id.in_(enroll_ids)).count() if enroll_ids else 0
        assignments = db.query(Assignment).filter(Assignment.subject_offering_id.in_(so_ids)).all() if so_ids else []
        assign_ids = [a.id for a in assignments]
        counts["Assignments"] = len(assignments)
        counts["Submissions"] = db.query(Submission).filter(Submission.assignment_id.in_(assign_ids)).count() if assign_ids else 0
        # counts["Internal Marks"] = db.query(InternalMark).filter(InternalMark.subject_offering_id.in_(so_ids)).count() if so_ids else 0
        docs = db.query(Document).filter(Document.subject_offering_id.in_(so_ids)).all() if so_ids else []
        doc_ids = [d.id for d in docs]
        counts["Documents"] = len(docs)
        counts["Document Chunks"] = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).count() if doc_ids else 0
        # Also: faculty, subjects under this dept
        counts["Faculty"] = db.query(Faculty).filter(Faculty.department_id == item_id).count()
        counts["Subjects"] = db.query(Subject).filter(Subject.department_id == item_id).count()
        # Student children
        counts["Reminders"] = db.query(Reminder).filter(Reminder.student_id.in_(student_ids)).count() if student_ids else 0
        counts["Semester History"] = db.query(StudentSemesterHistory).filter(StudentSemesterHistory.student_id.in_(student_ids)).count() if student_ids else 0

    elif entity == "batch":
        semesters = db.query(Semester).filter(Semester.batch_id == item_id).all()
        sem_ids = [s.id for s in semesters]
        counts["Semesters"] = len(semesters)
        counts["Students"] = db.query(Student).filter(Student.batch_id == item_id).count()
        student_ids = [s.id for s in db.query(Student).filter(Student.batch_id == item_id).all()]
        so = db.query(SubjectOffering).filter(SubjectOffering.semester_id.in_(sem_ids)).all() if sem_ids else []
        so_ids = [o.id for o in so]
        counts["Subject Offerings"] = len(so)
        enroll_ids = [e.id for e in db.query(Enrollment).filter(Enrollment.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Enrollments"] = len(enroll_ids)
        counts["Attendance Records"] = db.query(Attendance).filter(Attendance.enrollment_id.in_(enroll_ids)).count() if enroll_ids else 0
        assign_ids = [a.id for a in db.query(Assignment).filter(Assignment.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Assignments"] = len(assign_ids)
        counts["Submissions"] = db.query(Submission).filter(Submission.assignment_id.in_(assign_ids)).count() if assign_ids else 0
        # counts["Internal Marks"] = db.query(InternalMark).filter(InternalMark.subject_offering_id.in_(so_ids)).count() if so_ids else 0
        doc_ids = [d.id for d in db.query(Document).filter(Document.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Documents"] = len(doc_ids)
        counts["Document Chunks"] = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).count() if doc_ids else 0
        counts["Reminders"] = db.query(Reminder).filter(Reminder.student_id.in_(student_ids)).count() if student_ids else 0
        counts["Semester History"] = db.query(StudentSemesterHistory).filter(StudentSemesterHistory.student_id.in_(student_ids)).count() if student_ids else 0

    elif entity == "semester":
        so = db.query(SubjectOffering).filter(SubjectOffering.semester_id == item_id).all()
        so_ids = [o.id for o in so]
        counts["Subject Offerings"] = len(so)
        enroll_ids = [e.id for e in db.query(Enrollment).filter(Enrollment.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Enrollments"] = len(enroll_ids)
        counts["Attendance Records"] = db.query(Attendance).filter(Attendance.enrollment_id.in_(enroll_ids)).count() if enroll_ids else 0
        assign_ids = [a.id for a in db.query(Assignment).filter(Assignment.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Assignments"] = len(assign_ids)
        counts["Submissions"] = db.query(Submission).filter(Submission.assignment_id.in_(assign_ids)).count() if assign_ids else 0
        # counts["Internal Marks"] = db.query(InternalMark).filter(InternalMark.subject_offering_id.in_(so_ids)).count() if so_ids else 0
        doc_ids = [d.id for d in db.query(Document).filter(Document.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Documents"] = len(doc_ids)
        counts["Document Chunks"] = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).count() if doc_ids else 0
        counts["Semester History"] = db.query(StudentSemesterHistory).filter(StudentSemesterHistory.semester_id == item_id).count()
        # Students whose current_semester_id is this semester
        students = db.query(Student).filter(Student.current_semester_id == item_id).all()
        student_ids = [s.id for s in students]
        counts["Students"] = len(students)
        counts["Reminders"] = db.query(Reminder).filter(Reminder.student_id.in_(student_ids)).count() if student_ids else 0

    elif entity == "student":
        enroll_ids = [e.id for e in db.query(Enrollment).filter(Enrollment.student_id == item_id).all()]
        counts["Enrollments"] = len(enroll_ids)
        counts["Attendance Records"] = db.query(Attendance).filter(Attendance.enrollment_id.in_(enroll_ids)).count() if enroll_ids else 0
        counts["Submissions"] = db.query(Submission).filter(Submission.student_id == item_id).count()
        # counts["Internal Marks"] = db.query(InternalMark).filter(InternalMark.student_id == item_id).count()
        counts["Reminders"] = db.query(Reminder).filter(Reminder.student_id == item_id).count()
        counts["Semester History"] = db.query(StudentSemesterHistory).filter(StudentSemesterHistory.student_id == item_id).count()

    elif entity == "faculty":
        so_ids = [o.id for o in db.query(SubjectOffering).filter(SubjectOffering.faculty_id == item_id).all()]
        counts["Subject Offerings"] = len(so_ids)
        enroll_ids = [e.id for e in db.query(Enrollment).filter(Enrollment.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Enrollments"] = len(enroll_ids)
        counts["Attendance Records"] = db.query(Attendance).filter(Attendance.enrollment_id.in_(enroll_ids)).count() if enroll_ids else 0
        assign_ids = [a.id for a in db.query(Assignment).filter(Assignment.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Assignments"] = len(assign_ids)
        counts["Submissions"] = db.query(Submission).filter(Submission.assignment_id.in_(assign_ids)).count() if assign_ids else 0
        # counts["Internal Marks"] = db.query(InternalMark).filter(InternalMark.subject_offering_id.in_(so_ids)).count() if so_ids else 0
        doc_ids = [d.id for d in db.query(Document).filter(Document.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Documents"] = len(doc_ids)
        counts["Document Chunks"] = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).count() if doc_ids else 0

    elif entity == "subject":
        so_ids = [o.id for o in db.query(SubjectOffering).filter(SubjectOffering.subject_id == item_id).all()]
        counts["Subject Offerings"] = len(so_ids)
        enroll_ids = [e.id for e in db.query(Enrollment).filter(Enrollment.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Enrollments"] = len(enroll_ids)
        counts["Attendance Records"] = db.query(Attendance).filter(Attendance.enrollment_id.in_(enroll_ids)).count() if enroll_ids else 0
        assign_ids = [a.id for a in db.query(Assignment).filter(Assignment.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Assignments"] = len(assign_ids)
        counts["Submissions"] = db.query(Submission).filter(Submission.assignment_id.in_(assign_ids)).count() if assign_ids else 0
        # counts["Internal Marks"] = db.query(InternalMark).filter(InternalMark.subject_offering_id.in_(so_ids)).count() if so_ids else 0
        doc_ids = [d.id for d in db.query(Document).filter(Document.subject_offering_id.in_(so_ids)).all()] if so_ids else []
        counts["Documents"] = len(doc_ids)
        counts["Document Chunks"] = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).count() if doc_ids else 0

    elif entity == "subject-offering" or entity == "subject_offering":
        enroll_ids = [e.id for e in db.query(Enrollment).filter(Enrollment.subject_offering_id == item_id).all()]
        counts["Enrollments"] = len(enroll_ids)
        counts["Attendance Records"] = db.query(Attendance).filter(Attendance.enrollment_id.in_(enroll_ids)).count() if enroll_ids else 0
        assign_ids = [a.id for a in db.query(Assignment).filter(Assignment.subject_offering_id == item_id).all()]
        counts["Assignments"] = len(assign_ids)
        counts["Submissions"] = db.query(Submission).filter(Submission.assignment_id.in_(assign_ids)).count() if assign_ids else 0
        # counts["Internal Marks"] = db.query(InternalMark).filter(InternalMark.subject_offering_id == item_id).count()
        doc_ids = [d.id for d in db.query(Document).filter(Document.subject_offering_id == item_id).all()]
        counts["Documents"] = len(doc_ids)
        counts["Document Chunks"] = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).count() if doc_ids else 0

    elif entity == "enrollment":
        counts["Attendance Records"] = db.query(Attendance).filter(Attendance.enrollment_id == item_id).count()

    # Filter out zero counts
    return {k: v for k, v in counts.items() if v > 0}


def _cascade_delete_subject_offerings(db, so_ids):
    """Delete subject offerings and all their children."""
    if not so_ids: return
    enroll_ids = [e.id for e in db.query(Enrollment).filter(Enrollment.subject_offering_id.in_(so_ids)).all()]
    if enroll_ids:
        db.query(Attendance).filter(Attendance.enrollment_id.in_(enroll_ids)).delete(synchronize_session=False)
        db.query(Enrollment).filter(Enrollment.id.in_(enroll_ids)).delete(synchronize_session=False)
    assign_ids = [a.id for a in db.query(Assignment).filter(Assignment.subject_offering_id.in_(so_ids)).all()]
    if assign_ids:
        db.query(Submission).filter(Submission.assignment_id.in_(assign_ids)).delete(synchronize_session=False)
        db.query(Assignment).filter(Assignment.id.in_(assign_ids)).delete(synchronize_session=False)
    # db.query(InternalMark).filter(InternalMark.subject_offering_id.in_(so_ids)).delete(synchronize_session=False)
    doc_ids = [d.id for d in db.query(Document).filter(Document.subject_offering_id.in_(so_ids)).all()]
    if doc_ids:
        db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).delete(synchronize_session=False)
        db.query(Document).filter(Document.id.in_(doc_ids)).delete(synchronize_session=False)
    db.query(SubjectOffering).filter(SubjectOffering.id.in_(so_ids)).delete(synchronize_session=False)


def _cascade_delete_students(db, student_ids):
    """Delete students and all their children."""
    if not student_ids: return
    enroll_ids = [e.id for e in db.query(Enrollment).filter(Enrollment.student_id.in_(student_ids)).all()]
    if enroll_ids:
        db.query(Attendance).filter(Attendance.enrollment_id.in_(enroll_ids)).delete(synchronize_session=False)
        db.query(Enrollment).filter(Enrollment.id.in_(enroll_ids)).delete(synchronize_session=False)
    db.query(Submission).filter(Submission.student_id.in_(student_ids)).delete(synchronize_session=False)
    # db.query(InternalMark).filter(InternalMark.student_id.in_(student_ids)).delete(synchronize_session=False)
    db.query(Reminder).filter(Reminder.student_id.in_(student_ids)).delete(synchronize_session=False)
    db.query(StudentSemesterHistory).filter(StudentSemesterHistory.student_id.in_(student_ids)).delete(synchronize_session=False)
    # Get user_ids to delete them too
    user_ids = [s.user_id for s in db.query(Student).filter(Student.id.in_(student_ids)).all()]
    db.query(Student).filter(Student.id.in_(student_ids)).delete(synchronize_session=False)
    if user_ids:
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)


@router.get("/dependents/{entity}/{item_id}", summary="Check dependent records before delete")
def check_dependents(entity: str, item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    counts = _count_dependents(db, entity, item_id)
    return {"success": True, "data": counts}


@router.delete("/department/{item_id}", response_model=GenericAdminResponse, summary="Delete a Department")
def delete_department(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    obj = db.query(Department).filter(Department.id == item_id).first()
    if not obj: raise HTTPException(status_code=404, detail="Department not found")
    # Cascade: batches → semesters → subject_offerings → ..., students, faculty, subjects
    batches = db.query(Batch).filter(Batch.department_id == item_id).all()
    batch_ids = [b.id for b in batches]
    if batch_ids:
        semesters = db.query(Semester).filter(Semester.batch_id.in_(batch_ids)).all()
        sem_ids = [s.id for s in semesters]
        so_ids = [o.id for o in db.query(SubjectOffering).filter(SubjectOffering.semester_id.in_(sem_ids)).all()] if sem_ids else []
        _cascade_delete_subject_offerings(db, so_ids)
        student_ids = [s.id for s in db.query(Student).filter(Student.batch_id.in_(batch_ids)).all()]
        _cascade_delete_students(db, student_ids)
        if sem_ids:
            db.query(StudentSemesterHistory).filter(StudentSemesterHistory.semester_id.in_(sem_ids)).delete(synchronize_session=False)
            db.query(Semester).filter(Semester.id.in_(sem_ids)).delete(synchronize_session=False)
        db.query(Batch).filter(Batch.id.in_(batch_ids)).delete(synchronize_session=False)
    # Faculty & subjects under this dept — their own SO children
    fac_ids = [f.id for f in db.query(Faculty).filter(Faculty.department_id == item_id).all()]
    if fac_ids:
        fac_so_ids = [o.id for o in db.query(SubjectOffering).filter(SubjectOffering.faculty_id.in_(fac_ids)).all()]
        _cascade_delete_subject_offerings(db, fac_so_ids)
        db.query(Faculty).filter(Faculty.id.in_(fac_ids)).delete(synchronize_session=False)
    subj_ids = [s.id for s in db.query(Subject).filter(Subject.department_id == item_id).all()]
    if subj_ids:
        subj_so_ids = [o.id for o in db.query(SubjectOffering).filter(SubjectOffering.subject_id.in_(subj_ids)).all()]
        _cascade_delete_subject_offerings(db, subj_so_ids)
        db.query(Subject).filter(Subject.id.in_(subj_ids)).delete(synchronize_session=False)
    db.delete(obj)
    db.commit()
    return {"success": True, "data": f"Department #{item_id} and all dependents deleted"}

@router.delete("/batch/{item_id}", response_model=GenericAdminResponse, summary="Delete a Batch")
def delete_batch(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    obj = db.query(Batch).filter(Batch.id == item_id).first()
    if not obj: raise HTTPException(status_code=404, detail="Batch not found")
    semesters = db.query(Semester).filter(Semester.batch_id == item_id).all()
    sem_ids = [s.id for s in semesters]
    so_ids = [o.id for o in db.query(SubjectOffering).filter(SubjectOffering.semester_id.in_(sem_ids)).all()] if sem_ids else []
    _cascade_delete_subject_offerings(db, so_ids)
    student_ids = [s.id for s in db.query(Student).filter(Student.batch_id == item_id).all()]
    _cascade_delete_students(db, student_ids)
    if sem_ids:
        db.query(StudentSemesterHistory).filter(StudentSemesterHistory.semester_id.in_(sem_ids)).delete(synchronize_session=False)
        db.query(Semester).filter(Semester.id.in_(sem_ids)).delete(synchronize_session=False)
    db.delete(obj)
    db.commit()
    return {"success": True, "data": f"Batch #{item_id} and all dependents deleted"}

@router.delete("/semester/{item_id}", response_model=GenericAdminResponse, summary="Delete a Semester")
def delete_semester(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    obj = db.query(Semester).filter(Semester.id == item_id).first()
    if not obj: raise HTTPException(status_code=404, detail="Semester not found")
    so_ids = [o.id for o in db.query(SubjectOffering).filter(SubjectOffering.semester_id == item_id).all()]
    _cascade_delete_subject_offerings(db, so_ids)
    # Delete students whose current_semester_id is this semester
    student_ids = [s.id for s in db.query(Student).filter(Student.current_semester_id == item_id).all()]
    _cascade_delete_students(db, student_ids)
    db.query(StudentSemesterHistory).filter(StudentSemesterHistory.semester_id == item_id).delete(synchronize_session=False)
    db.delete(obj)
    db.commit()
    return {"success": True, "data": f"Semester #{item_id} and all dependents deleted"}

@router.delete("/student/{item_id}", response_model=GenericAdminResponse, summary="Delete a Student")
def delete_student(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    obj = db.query(Student).filter(Student.id == item_id).first()
    if not obj: raise HTTPException(status_code=404, detail="Student not found")
    _cascade_delete_students(db, [item_id])
    return {"success": True, "data": f"Student #{item_id} and all dependents deleted"}

@router.delete("/faculty/{item_id}", response_model=GenericAdminResponse, summary="Delete a Faculty")
def delete_faculty(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    obj = db.query(Faculty).filter(Faculty.id == item_id).first()
    if not obj: raise HTTPException(status_code=404, detail="Faculty not found")
    so_ids = [o.id for o in db.query(SubjectOffering).filter(SubjectOffering.faculty_id == item_id).all()]
    _cascade_delete_subject_offerings(db, so_ids)
    user_id = obj.user_id
    db.delete(obj)
    if user_id:
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()
    return {"success": True, "data": f"Faculty #{item_id} and all dependents deleted"}

@router.delete("/subject/{item_id}", response_model=GenericAdminResponse, summary="Delete a Subject")
def delete_subject(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    obj = db.query(Subject).filter(Subject.id == item_id).first()
    if not obj: raise HTTPException(status_code=404, detail="Subject not found")
    so_ids = [o.id for o in db.query(SubjectOffering).filter(SubjectOffering.subject_id == item_id).all()]
    _cascade_delete_subject_offerings(db, so_ids)
    db.delete(obj)
    db.commit()
    return {"success": True, "data": f"Subject #{item_id} and all dependents deleted"}

@router.delete("/subject-offering/{item_id}", response_model=GenericAdminResponse, summary="Delete a Subject Offering")
def delete_subject_offering(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    obj = db.query(SubjectOffering).filter(SubjectOffering.id == item_id).first()
    if not obj: raise HTTPException(status_code=404, detail="Subject Offering not found")
    _cascade_delete_subject_offerings(db, [item_id])
    db.commit()
    return {"success": True, "data": f"Subject Offering #{item_id} and all dependents deleted"}

@router.delete("/enrollment/{item_id}", response_model=GenericAdminResponse, summary="Delete an Enrollment")
def delete_enrollment(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    obj = db.query(Enrollment).filter(Enrollment.id == item_id).first()
    if not obj: raise HTTPException(status_code=404, detail="Enrollment not found")
    db.query(Attendance).filter(Attendance.enrollment_id == item_id).delete(synchronize_session=False)
    db.delete(obj)
    db.commit()
    return {"success": True, "data": f"Enrollment #{item_id} and all dependents deleted"}



@router.post("/upload-pdf")
def upload_pdf(
    subject_id: int,
    module_number: int,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admin can upload PDFs")

    if module_number < 1 or module_number > 4:
        raise HTTPException(status_code=400, detail="Module number must be between 1 and 4")

    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")

    file_path = os.path.join(UPLOAD_PATH, file.filename)

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    # Build FAISS index using subject_id
    build_index(subject_id, file_path)

    # Save document record
    document = Document(
        subject_offering_id=None,
        title=file.filename,
        file_url=file_path,
        document_type=f"Module {module_number}",
        uploaded_by=current_user.id
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # Store subject mapping in a simple way — add subject_id info to title
    document.title = f"[Subject #{subject_id}: {subj.subject_name}] {file.filename}"
    db.commit()

    return {
        "success": True,
        "data": f"Module {module_number} PDF for '{subj.subject_name}' uploaded and indexed successfully"
    }

@router.get("/documents", summary="List all uploaded documents")
def list_documents(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    docs = db.query(Document).all()
    result = []
    for d in docs:
        uploader = db.query(User).filter(User.id == d.uploaded_by).first() if d.uploaded_by else None
        result.append({
            "id": d.id,
            "title": d.title or "Untitled",
            "type": d.document_type or "N/A",
            "uploaded_by": uploader.name if uploader else "System",
            "uploaded_at": str(d.uploaded_at)[:16] if d.uploaded_at else "N/A"
        })
    return {"success": True, "data": result}

@router.delete("/document/{item_id}", response_model=GenericAdminResponse, summary="Delete a Document")
def delete_document(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "admin": raise HTTPException(status_code=403, detail="Admin only")
    obj = db.query(Document).filter(Document.id == item_id).first()
    if not obj: raise HTTPException(status_code=404, detail="Document not found")
    # Cascade: delete document chunks
    db.query(DocumentChunk).filter(DocumentChunk.document_id == item_id).delete(synchronize_session=False)
    db.delete(obj)
    db.commit()
    return {"success": True, "data": f"Document #{item_id} deleted"}


@router.post("/promote/{batch_id}")
def promote_batch(
    batch_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admin can promote batches")

    # Get all students in the batch
    students = db.query(Student).filter(Student.batch_id == batch_id).all()
    if not students:
        raise HTTPException(status_code=404, detail="No students found in this batch")

    # Find active semester for this batch
    current_sem = db.query(Semester).filter(
        Semester.batch_id == batch_id,
        Semester.is_active == 1
    ).first()

    if not current_sem:
        raise HTTPException(status_code=400, detail="No active semester found for this batch")

    # Find next semester
    next_sem = db.query(Semester).filter(
        Semester.batch_id == batch_id,
        Semester.semester_number == current_sem.semester_number + 1
    ).first()

    history_records = []
    
    for student in students:
        # Get performance summary for current semester subjects
        summary = get_student_performance_summary(db, student.id)
        
        if summary:
            avg_attendance = sum(s['attendance'] for s in summary) / len(summary)
            avg_marks = sum(s['avg_marks'] for s in summary) / len(summary)
            total_missed = sum(s['missed_assignments'] for s in summary)
        else:
            avg_attendance = 0
            avg_marks = 0
            total_missed = 0

        # Create Semester History Record
        history_records.append(
            StudentSemesterHistory(
                student_id=student.id,
                semester_id=current_sem.id,
                average_attendance=int(avg_attendance),
                average_marks=int(avg_marks),
                total_missed_assignments=total_missed
            )
        )

        # Update student's current semester pointer
        if next_sem:
            student.current_semester_id = next_sem.id
        else:
            # Graduated / No future semester explicitly marked
            student.current_semester_id = None 

    db.add_all(history_records)

    # Deactivate current semester, activate next
    current_sem.is_active = 0
    if next_sem:
        next_sem.is_active = 1

    db.commit()

    return {
        "success": True,
        "data": f"Batch {batch_id} promoted successfully. Archived {len(history_records)} metrics."
    }


