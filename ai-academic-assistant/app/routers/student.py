from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import os

from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.models.assignment import Assignment, Submission, InternalMark
from app.models.academic import Student, Enrollment, SubjectOffering, Subject
from app.services.attendance_service import calculate_attendance_percentage
from app.services.ai_service import get_student_performance_summary

router = APIRouter(prefix="/student", tags=["Student"])

UPLOAD_DIR = "student_submissions"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -------- Pydantic Schemas --------

class AssignmentResponse(BaseModel):
    id: int
    title: str
    deadline: datetime
    subject_offering_id: int

class MarksResponse(BaseModel):
    subject_offering_id: int
    marks_obtained: float
    max_marks: float

class AttendanceResponse(BaseModel):
    subject: str
    percentage: float

class GenericResponse(BaseModel):
    success: bool
    data: str

class AnalyticsMarksTrend(BaseModel):
    subject: str
    score: float
    max: float
    date: str

class AnalyticsRiskRanking(BaseModel):
    subject: str
    risk_score: int
    risk_label: str

class DashboardAnalyticsData(BaseModel):
    marks_trend: List[AnalyticsMarksTrend]
    attendance_graph: List[AttendanceResponse]
    risk_ranking: List[AnalyticsRiskRanking]
    weak_subjects: List[str]

class DashboardAnalyticsResponse(BaseModel):
    success: bool
    data: DashboardAnalyticsData

class StudentAssignmentsResponse(BaseModel):
    success: bool
    data: List[AssignmentResponse]

class StudentMarksResponse(BaseModel):
    success: bool
    data: List[MarksResponse]

class StudentAttendanceResponse(BaseModel):
    success: bool
    data: List[AttendanceResponse]


class SubjectInformation(BaseModel):
    subject_offering_id: int
    subject_name: str
    subject_code: str
    faculty_name: str

class StudentSubjectsResponse(BaseModel):
    success: bool
    data: List[SubjectInformation]

# -------- View Enrolled Subjects --------

@router.get("/subjects", response_model=StudentSubjectsResponse, summary="Get student's enrolled subjects")
def view_subjects(
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

    subjects_data = []
    
    from app.models.academic import Faculty

    for e in enrollments:
        offering = db.query(SubjectOffering).filter(SubjectOffering.id == e.subject_offering_id).first()
        if not offering: continue
        
        subject = db.query(Subject).filter(Subject.id == offering.subject_id).first()
        faculty = db.query(Faculty).filter(Faculty.id == offering.faculty_id).first()
        faculty_user = db.query(User).filter(User.id == faculty.user_id).first() if faculty else None
        
        subjects_data.append({
            "subject_offering_id": offering.id,
            "subject_name": subject.subject_name if subject else "Unknown",
            "subject_code": subject.subject_code if subject else "Unknown",
            "faculty_name": faculty_user.name if faculty_user else "Unknown Faculty"
        })

    return {"success": True, "data": subjects_data}


# -------- View Assignments --------

@router.get("/assignments", response_model=StudentAssignmentsResponse, summary="Get student assignments")
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

@router.get("/marks", response_model=StudentMarksResponse, summary="Get student marks")
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

@router.post("/submit-assignment", response_model=GenericResponse, summary="Submit an assignment file")
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


# -------- View Attendance --------

@router.get("/attendance", response_model=StudentAttendanceResponse, summary="Get student attendance")
def view_attendance(
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

    attendance_data = []

    for e in enrollments:
        offering = db.query(SubjectOffering).filter(SubjectOffering.id == e.subject_offering_id).first()
        if not offering:
            continue
            
        subject = db.query(Subject).filter(Subject.id == offering.subject_id).first()
        subject_name = subject.subject_name if subject else "Unknown Subject"

        percentage = calculate_attendance_percentage(db, student.id, e.subject_offering_id)

        attendance_data.append({
            "subject": subject_name,
            "percentage": percentage
        })

    return {"success": True, "data": attendance_data}


# -------- Student Dashboard Analytics --------

@router.get("/dashboard/analytics", response_model=DashboardAnalyticsResponse, summary="Get advanced analytics for student dashboard")
def student_dashboard_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "student":
        raise HTTPException(status_code=403, detail="Only students allowed")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    summary = get_student_performance_summary(db, student.id)
    
    marks_trend = []
    marks = db.query(InternalMark).filter(InternalMark.student_id == student.id).order_by(InternalMark.created_at).all()
    for m in marks:
        subject = db.query(SubjectOffering).join(Subject).filter(SubjectOffering.id == m.subject_offering_id).first()
        marks_trend.append({
            "subject": subject.subject.subject_name if subject else "Unknown",
            "score": m.marks_obtained,
            "max": m.max_marks,
            "date": m.created_at.strftime("%Y-%m-%d") if m.created_at else "Unknown"
        })

    attendance_graph = []
    risk_ranking = []
    weak_subjects = []

    for item in summary:
        attendance_graph.append({
            "subject": item["subject"],
            "percentage": item["attendance"]
        })
        
        # We can rank by risk level: High = 3, Medium = 2, Low = 1
        num_risk = 3 if item["risk_level"] == "High" else (2 if item["risk_level"] == "Medium" else 1)
        risk_ranking.append({
            "subject": item["subject"],
            "risk_score": num_risk,
            "risk_label": item["risk_level"]
        })

        if item["risk_level"] == "High":
            weak_subjects.append(item["subject"])

    # Sort risk ranking descending
    risk_ranking.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "success": True,
        "data": {
            "marks_trend": marks_trend,
            "attendance_graph": attendance_graph,
            "risk_ranking": risk_ranking,
            "weak_subjects": weak_subjects
        }
    }
