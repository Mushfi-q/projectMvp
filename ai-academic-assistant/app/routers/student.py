from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import os

from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.models.assignment import Assignment, Submission
from app.models.academic import Student, Enrollment, SubjectOffering, Subject
from app.models.reminder import Reminder
from app.services.attendance_service import calculate_attendance_percentage
from app.services.ai_service import get_student_performance_summary, calculate_average_marks

router = APIRouter(prefix="/student", tags=["Student"])

UPLOAD_DIR = "student_submissions"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -------- Pydantic Schemas --------

class AssignmentResponse(BaseModel):
    id: int
    title: str
    deadline: datetime
    subject_offering_id: Optional[int] = None
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    is_submitted: bool
    marks: Optional[int] = None
    type: str = "assignment"

class MarksResponse(BaseModel):
    subject_offering_id: int
    marks_obtained: float
    max_marks: float

class AttendanceResponse(BaseModel):
    subject: str
    percentage: float
    present_hours: int = 0
    total_hours: int = 0

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

        offering = db.query(SubjectOffering).filter(SubjectOffering.id == e.subject_offering_id).first()
        subject = db.query(Subject).filter(Subject.id == offering.subject_id).first() if offering else None

        for a in subject_assignments:
            submission = db.query(Submission).filter(
                Submission.assignment_id == a.id,
                Submission.student_id == student.id
            ).first()
            
            assignments.append({
                "id": a.id,
                "title": a.title,
                "deadline": a.deadline,
                "subject_offering_id": a.subject_offering_id,
                "subject_code": subject.subject_code if subject else "Unknown",
                "subject_name": subject.subject_name if subject else "Unknown",
                "is_submitted": submission is not None,
                "marks": submission.marks if submission else None,
                "type": "assignment"
            })

    # Fetch Reminders
    reminders = db.query(Reminder).filter(Reminder.student_id == student.id).all()
    for r in reminders:
        assignments.append({
            "id": r.id,
            "title": r.title,
            "deadline": r.due_date,
            "subject_offering_id": None,
            "subject_code": None,
            "subject_name": None,
            "is_submitted": r.is_completed,
            "marks": None,
            "type": "reminder"
        })

    # Sort by deadline descending so history puts newest past tasks first
    assignments.sort(key=lambda x: x["deadline"], reverse=True)

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

    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id
    ).all()

    result = []

    for e in enrollments:
        avg = calculate_average_marks(db, student.id, e.subject_offering_id)
        
        if isinstance(avg, (int, float)):
            result.append({
                "subject_offering_id": e.subject_offering_id,
                "marks_obtained": avg,
                "max_marks": 100.0  # By convention, percentages are out of 100
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


# -------- Complete Reminder --------

@router.post("/complete-reminder/{reminder_id}", response_model=GenericResponse, summary="Mark a reminder as completed")
def complete_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "student":
        raise HTTPException(status_code=403, detail="Only students allowed")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    reminder = db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.student_id == student.id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    reminder.is_completed = True
    db.commit()

    return {"success": True, "data": "Reminder marked as completed"}


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

        att_info = calculate_attendance_percentage(db, student.id, e.subject_offering_id)

        attendance_data.append({
            "subject": subject_name,
            "percentage": att_info["percentage"],
            "present_hours": att_info["present_hours"],
            "total_hours": att_info["total_hours"]
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
    submissions = db.query(Submission).filter(
        Submission.student_id == student.id,
        Submission.marks.isnot(None)
    ).order_by(Submission.submitted_at).all()
    
    for sub in submissions:
        assignment = db.query(Assignment).filter(Assignment.id == sub.assignment_id).first()
        if not assignment: continue
        
        offering = db.query(SubjectOffering).filter(SubjectOffering.id == assignment.subject_offering_id).first()
        if not offering: continue
        
        subject = db.query(Subject).filter(Subject.id == offering.subject_id).first()
        
        marks_trend.append({
            "subject": subject.subject_name if subject else "Unknown",
            "score": sub.marks,
            "max": 100.0,
            "date": sub.submitted_at.strftime("%Y-%m-%d") if sub.submitted_at else "Unknown"
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
