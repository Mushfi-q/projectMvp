from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.models.assignment import Assignment, InternalMark
from app.models.academic import Faculty, SubjectOffering, Enrollment, Student

router = APIRouter(prefix="/faculty", tags=["Faculty"])


# -------- Request Schemas --------

class AssignmentCreate(BaseModel):
    subject_offering_id: int
    title: str
    description: str
    deadline: datetime


class MarkUpload(BaseModel):
    subject_offering_id: int
    student_id: int
    marks_obtained: int
    max_marks: int


# -------- Create Assignment --------

@router.post("/assignment")
def create_assignment(
    data: AssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")

    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")

    offering = db.query(SubjectOffering).filter(
        SubjectOffering.id == data.subject_offering_id,
        SubjectOffering.faculty_id == faculty.id
    ).first()

    if not offering:
        raise HTTPException(status_code=403, detail="You do not own this subject")

    assignment = Assignment(
        subject_offering_id=data.subject_offering_id,
        title=data.title,
        description=data.description,
        deadline=data.deadline
    )

    db.add(assignment)
    db.commit()

    return {"success": True, "data": "Assignment created"}


# -------- Upload Marks --------

@router.post("/marks")
def upload_marks(
    data: MarkUpload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")

    mark = InternalMark(
        subject_offering_id=data.subject_offering_id,
        student_id=data.student_id,
        marks_obtained=data.marks_obtained,
        max_marks=data.max_marks
    )

    db.add(mark)
    db.commit()

    return {"success": True, "data": "Marks uploaded"}


# -------- View Students in Subject --------

@router.get("/students/{subject_offering_id}")
def list_students(
    subject_offering_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")

    enrollments = db.query(Enrollment).filter(
        Enrollment.subject_offering_id == subject_offering_id
    ).all()

    student_list = []

    for e in enrollments:
        student = db.query(Student).filter(Student.id == e.student_id).first()
        if student:
            student_list.append({
                "student_id": student.id,
                "register_number": student.register_number
            })

    return {"success": True, "data": student_list}
