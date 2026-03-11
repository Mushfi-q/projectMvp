from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional

from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.models.assignment import Assignment, Submission
from app.models.academic import Faculty, SubjectOffering, Enrollment, Student
from app.services.attendance_service import mark_attendance, calculate_attendance_percentage
from app.services.ai_service import get_student_performance_summary, calculate_average_marks

router = APIRouter(prefix="/faculty", tags=["Faculty"])


# -------- Request Schemas --------

class AssignmentCreate(BaseModel):
    subject_offering_id: int
    title: str
    description: str
    deadline: datetime


class GenericFacultyResponse(BaseModel):
    success: bool
    data: str





class AttendanceRecord(BaseModel):
    student_id: int
    status: str

class BulkAttendanceRequest(BaseModel):
    subject_offering_id: int
    date: str
    hours: int
    records: List[AttendanceRecord]

class GenericFacultyResponse(BaseModel):
    success: bool
    data: str

class StudentListResponseData(BaseModel):
    student_id: int
    register_number: str
    attendance: float
    marks: float

class StudentListResponse(BaseModel):
    success: bool
    data: List[StudentListResponseData]


class AssignmentSubmissionData(BaseModel):
    submission_id: int
    student_id: int
    register_number: str
    student_name: str
    file_url: str
    submitted_at: datetime
    marks: Optional[int]
    feedback: Optional[str]

class AssignmentSubmissionsResponse(BaseModel):
    success: bool
    data: List[AssignmentSubmissionData]

class GradeSubmissionRequest(BaseModel):
    marks: int
    feedback: Optional[str] = None

class FacultyAnalyticsLowPerformer(BaseModel):
    student_id: int
    register_number: str
    risk_level: str
    attendance: float
    avg_marks: float

class FacultyAnalyticsData(BaseModel):
    class_average: float
    class_attendance_summary: float
    assignment_completion_rate: float
    low_performers: List[FacultyAnalyticsLowPerformer]
    total_students: int

class FacultyAnalyticsResponse(BaseModel):
    success: bool
    data: FacultyAnalyticsData

class BulkAttendanceResponse(BaseModel):
    success: bool
    marked: int
    absences_alerted: int
    details: str

class AttendanceHistoryItem(BaseModel):
    date: date
    hours: int
    present_count: int
    absent_count: int

class AttendanceHistoryResponse(BaseModel):
    success: bool
    data: List[AttendanceHistoryItem]


@router.get("/subjects", summary="List all Subjects for dropdown")
def list_subjects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")
    from app.models.academic import Subject, Department
    subjects = db.query(Subject).all()
    result = []
    for s in subjects:
        dept = db.query(Department).filter(Department.id == s.department_id).first()
        result.append({
            "id": s.id,
            "subject_name": s.subject_name,
            "subject_code": s.subject_code,
            "department": dept.name if dept else "Unknown"
        })
    return {"success": True, "data": result}


@router.get("/semesters", summary="List all Semesters for dropdown")
def list_semesters(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")
    from app.models.academic import Semester, Batch
    semesters = db.query(Semester).all()
    result = []
    for s in semesters:
        batch = db.query(Batch).filter(Batch.id == s.batch_id).first()
        result.append({
            "id": s.id,
            "batch": f"{batch.start_year}-{batch.end_year}" if batch else "N/A",
            "semester_number": s.semester_number,
        })
    return {"success": True, "data": result}


@router.get("/my-subjects", summary="Get all subject offerings assigned to the logged-in faculty")
def get_my_subjects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")

    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")

    from app.models.academic import SubjectOffering
    # Get all offerings for this faculty
    offerings = db.query(SubjectOffering).filter(SubjectOffering.faculty_id == faculty.id).all()
    
    result = []
    for o in offerings:
        result.append({
            "subject_offering_id": o.id,
            "subject_id": o.subject_id,
            "subject_name": o.subject.subject_name if o.subject else "Unknown",
            "subject_code": o.subject.subject_code if o.subject else "Unknown",
            "semester_id": o.semester_id
        })
        
    return {"success": True, "data": result}

# -------- Assignments --------

@router.get("/assignments", summary="Get all assignments created by the logged-in faculty")
def get_faculty_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")

    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")

    from app.models.academic import SubjectOffering
    from app.models.assignment import Assignment

    # Find all subject offerings for this faculty
    so_ids = [o.id for o in db.query(SubjectOffering).filter(SubjectOffering.faculty_id == faculty.id).all()]
    if not so_ids:
        return {"success": True, "data": []}

    assignments = db.query(Assignment).filter(Assignment.subject_offering_id.in_(so_ids)).order_by(Assignment.deadline.desc()).all()
    
    result = []
    for a in assignments:
        so = db.query(SubjectOffering).filter(SubjectOffering.id == a.subject_offering_id).first()
        result.append({
            "id": a.id,
            "title": a.title,
            "subject_code": so.subject.subject_code if so and so.subject else "N/A",
            "subject_name": so.subject.subject_name if so and so.subject else "N/A",
            "semester_id": so.semester_id if so else "N/A",
            "deadline": a.deadline.isoformat() if a.deadline else None,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })
        
    return {"success": True, "data": result}


@router.post("/assignment", response_model=GenericFacultyResponse, summary="Create a new assignment")
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


# -------- View & Grade Submissions --------

@router.get("/assignment/{assignment_id}/submissions", response_model=AssignmentSubmissionsResponse, summary="Get all submissions for an assignment")
def get_assignment_submissions(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    
    result = []
    for sub in submissions:
        student = db.query(Student).filter(Student.id == sub.student_id).first()
        student_user = db.query(User).filter(User.id == student.user_id).first() if student else None
        
        result.append({
            "submission_id": sub.id,
            "student_id": sub.student_id,
            "register_number": student.register_number if student else "Unknown",
            "student_name": student_user.name if student_user else "Unknown Student",
            "file_url": sub.file_url.replace("\\", "/") if sub.file_url else "",
            "submitted_at": sub.submitted_at,
            "marks": sub.marks,
            "feedback": sub.feedback
        })
        
    return {"success": True, "data": result}
    

@router.post("/submission/{submission_id}/grade", response_model=GenericFacultyResponse, summary="Grade a student submission")
def grade_submission(
    submission_id: int,
    data: GradeSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")

    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.marks = data.marks
    submission.feedback = data.feedback
    
    db.commit()

    return {"success": True, "data": "Grade saved successfully"}





# -------- View Students in Subject --------

@router.get("/students/{subject_offering_id}", response_model=StudentListResponse, summary="List all students in a subject offering")
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
            calc_attendance_info = calculate_attendance_percentage(db, student.id, subject_offering_id)
            calc_attendance = calc_attendance_info["percentage"]
            calc_marks = calculate_average_marks(db, student.id, subject_offering_id)
            
            # Handle empty strings from AI service
            marks_val = float(calc_marks) if isinstance(calc_marks, (int, float)) else 0.0

            student_list.append({
                "student_id": student.id,
                "register_number": student.register_number,
                "attendance": float(calc_attendance),
                "marks": marks_val
            })

    return {"success": True, "data": student_list}


# -------- Mark Bulk Attendance --------

@router.post("/attendance/bulk", response_model=BulkAttendanceResponse, summary="Mark bulk attendance for a class")
def bulk_mark_attendance(
    data: BulkAttendanceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")

    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")

    # Verify ownership of SubjectOffering
    offering = db.query(SubjectOffering).filter(
        SubjectOffering.id == data.subject_offering_id,
        SubjectOffering.faculty_id == faculty.id
    ).first()

    if not offering:
        raise HTTPException(status_code=403, detail="You do not own this subject")

    try:
        attendance_date = datetime.strptime(data.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    records_native = [record.model_dump() for record in data.records]

    result = mark_attendance(db, data.subject_offering_id, records_native, attendance_date, data.hours)
    return {"success": True, **result}


# -------- Attendance History --------

@router.get("/attendance/history/{subject_offering_id}", response_model=AttendanceHistoryResponse, summary="Get attendance history for a subject")
def get_attendance_history(subject_offering_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")
        
    from app.models.academic import Enrollment
    from app.models.attendance import Attendance
    from sqlalchemy import func, case
    
    present_case = case((Attendance.status == 'Present', 1), else_=0)
    absent_case = case((Attendance.status == 'Absent', 1), else_=0)
    
    records = db.query(
        Attendance.date,
        Attendance.hours,
        func.sum(present_case).label('present_count'),
        func.sum(absent_case).label('absent_count')
    ).join(Enrollment, Attendance.enrollment_id == Enrollment.id)\
     .filter(Enrollment.subject_offering_id == subject_offering_id)\
     .group_by(Attendance.date, Attendance.hours)\
     .order_by(Attendance.date.desc())\
     .all()
     
    history = []
    for r in records:
        history.append({
            "date": r.date,
            "hours": r.hours,
            "present_count": r.present_count or 0,
            "absent_count": r.absent_count or 0
        })
        
    return {"success": True, "data": history}


# -------- Faculty Dashboard Analytics --------

@router.get("/analytics/{subject_offering_id}", response_model=FacultyAnalyticsResponse, summary="Get advanced analytics for faculty dashboard")
def faculty_dashboard_analytics(
    subject_offering_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty allowed")

    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")

    offering = db.query(SubjectOffering).filter(
        SubjectOffering.id == subject_offering_id,
        SubjectOffering.faculty_id == faculty.id
    ).first()

    if not offering:
        raise HTTPException(status_code=403, detail="You do not own this subject")

    enrollments = db.query(Enrollment).filter(Enrollment.subject_offering_id == subject_offering_id).all()
    student_ids = [e.student_id for e in enrollments]
    total_students = len(student_ids)

    # 1. Class Average
    # We calculate class average by averaging each student's auto-calculated assignment average
    student_averages = []
    for sid in student_ids:
        avg = calculate_average_marks(db, sid, subject_offering_id)
        if isinstance(avg, (int, float)):
            student_averages.append(avg)

    class_average = round(sum(student_averages) / len(student_averages), 2) if student_averages else 0.0

    # 2. Low-Performing Students & Attendance Summary
    low_performers = []
    attendance_sum = 0

    for sid in student_ids:
        # Get risk from ai_service
        summary = get_student_performance_summary(db, sid)
        st_obj = db.query(Student).filter(Student.id == sid).first()
        for item in summary:
            if item["subject"] == offering.subject.subject_name:
                attendance_sum += item["attendance"]
                if item["risk_level"] == "High":
                    low_performers.append({
                        "student_id": sid,
                        "register_number": st_obj.register_number,
                        "risk_level": "High",
                        "attendance": item["attendance"],
                        "avg_marks": item["avg_marks"]
                    })

    class_attendance_summary = round(attendance_sum / total_students if total_students > 0 else 0, 2)

    # 3. Assignment Completion Rate
    assignments = db.query(Assignment).filter(Assignment.subject_offering_id == subject_offering_id).all()
    total_assignments_expected = len(assignments) * total_students
    if total_assignments_expected > 0:
        assignment_ids = [a.id for a in assignments]
        total_submissions = db.query(Submission.student_id, Submission.assignment_id).filter(
            Submission.assignment_id.in_(assignment_ids)
        ).distinct().count()
        completion_rate = min(100.0, round((total_submissions / total_assignments_expected) * 100, 2))
    else:
        completion_rate = 0.0

    return {
        "success": True,
        "data": {
            "class_average": class_average,
            "class_attendance_summary": class_attendance_summary,
            "assignment_completion_rate": completion_rate,
            "low_performers": low_performers,
            "total_students": total_students
        }
    }
