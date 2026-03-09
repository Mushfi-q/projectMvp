from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.models.assignment import Assignment, InternalMark, Submission
from app.models.academic import Faculty, SubjectOffering, Enrollment, Student
from app.services.attendance_service import mark_attendance, calculate_attendance_percentage
from app.services.ai_service import get_student_performance_summary

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


class MarkUpload(BaseModel):
    subject_offering_id: int
    student_id: int
    marks_obtained: int
    max_marks: int


class AttendanceRecord(BaseModel):
    student_id: int
    status: str

class BulkAttendanceRequest(BaseModel):
    subject_offering_id: int
    date: str
    records: List[AttendanceRecord]

class GenericFacultyResponse(BaseModel):
    success: bool
    data: str

class StudentListResponseData(BaseModel):
    student_id: int
    register_number: str

class StudentListResponse(BaseModel):
    success: bool
    data: List[StudentListResponseData]

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


# -------- Upload Marks --------

@router.post("/marks", response_model=GenericFacultyResponse, summary="Upload student marks")
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
            student_list.append({
                "student_id": student.id,
                "register_number": student.register_number
            })

    return {"success": True, "data": student_list}


# -------- Mark Bulk Attendance --------

@router.post("/attendance", response_model=BulkAttendanceResponse, summary="Mark bulk attendance for a class")
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

    result = mark_attendance(db, data.subject_offering_id, records_native, attendance_date)
    return {"success": True, **result}


# -------- Faculty Dashboard Analytics --------

@router.get("/dashboard/analytics/{subject_offering_id}", response_model=FacultyAnalyticsResponse, summary="Get advanced analytics for faculty dashboard")
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
    marks = db.query(InternalMark).filter(InternalMark.subject_offering_id == subject_offering_id).all()
    total_obtained = sum(m.marks_obtained for m in marks)
    total_max = sum(m.max_marks for m in marks)
    class_average = round((total_obtained / total_max * 100) if total_max > 0 else 0, 2)

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
        total_submissions = db.query(Submission).filter(Submission.assignment_id.in_(assignment_ids)).count()
        completion_rate = round((total_submissions / total_assignments_expected) * 100, 2)
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
