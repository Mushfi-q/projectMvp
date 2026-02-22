from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import os

from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.models.assignment import Assignment, Submission, InternalMark
from app.models.academic import Student, Enrollment

router = APIRouter(prefix="/student", tags=["Student"])

UPLOAD_DIR = "student_submissions"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -------- View Assignments --------

@router.get("/assignments")
def view_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "student":
        raise HTTPException(status_code=403, detail="Only students allowed")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id
    ).all()

    assignments = []

    for e in enrollments:
        # Note: In a real app, you might want to join these queries or filter differently
        subject_assignments = db.query(Assignment).filter(
            Assignment.subject_offering_id == e.subject_offering_id
        ).all()

        for a in subject_assignments:
            assignments.append({
                "id": a.id,
                "title": a.title,
                "deadline": a.deadline,
                "subject_offering_id": a.subject_offering_id
            })

    return {"success": True, "data": assignments}


# -------- View Marks --------

@router.get("/marks")
def view_marks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "student":
        raise HTTPException(status_code=403, detail="Only students allowed")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    marks = db.query(InternalMark).filter(
        InternalMark.student_id == student.id
    ).all()

    result = []

    for m in marks:
        result.append({
            "subject_offering_id": m.subject_offering_id,
            "marks_obtained": m.marks_obtained,
            "max_marks": m.max_marks
        })

    return {"success": True, "data": result}


# -------- Submit Assignment --------

@router.post("/submit-assignment")
async def submit_assignment(
    assignment_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "student":
        raise HTTPException(status_code=403, detail="Only students allowed")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    # Ensure unique filename to prevent overwrites or just use timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{student.id}_{assignment_id}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    submission = Submission(
        assignment_id=assignment_id,
        student_id=student.id,
        file_url=file_path,
        submitted_at=datetime.utcnow()
    )

    db.add(submission)
    db.commit()

    return {"success": True, "data": "Assignment submitted"}
