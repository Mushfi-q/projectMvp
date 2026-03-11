from datetime import date
from sqlalchemy.orm import Session
from app.models.academic import Enrollment
from app.models.attendance import Attendance

def mark_attendance(db: Session, subject_offering_id: int, attendance_data: list[dict], attendance_date: date = None, hours: int = 1):
    """
    attendance_data = [
        {"student_id": 1, "status": "Present"},
        {"student_id": 2, "status": "Absent"}
    ]
    """
    if attendance_date is None:
        attendance_date = date.today()

    # Get all enrollments for this subject_offering to validate student_ids
    enrollments = db.query(Enrollment).filter(Enrollment.subject_offering_id == subject_offering_id).all()
    enrollment_map = {e.student_id: e for e in enrollments}

    records_to_insert = []
    
    for item in attendance_data:
        student_id = item.get("student_id")
        status = item.get("status")
        
        # Only process if the student is actually enrolled
        if student_id in enrollment_map:
            enrollment = enrollment_map[student_id]
            
            # Check if attendance already marked for this date
            existing = db.query(Attendance).filter(
                Attendance.enrollment_id == enrollment.id,
                Attendance.date == attendance_date
            ).first()

            if existing:
                # Update existing
                existing.status = status
                existing.hours = hours
            else:
                # Create new
                records_to_insert.append(
                    Attendance(
                        enrollment_id=enrollment.id,
                        date=attendance_date,
                        status=status,
                        hours=hours
                    )
                )

    if records_to_insert:
        db.add_all(records_to_insert)
        
    db.commit()
    
    absent_count = sum(1 for item in attendance_data if item.get("status") == "Absent")
    total_marked = len(attendance_data)
    
    return {
        "marked": total_marked,
        "absences_alerted": absent_count,
        "details": f"Attendance marked for {total_marked} students. {absent_count} absences recorded."
    }

def calculate_attendance_percentage(db: Session, student_id: int, subject_offering_id: int):
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.subject_offering_id == subject_offering_id
    ).first()

    if not enrollment:
        return {"percentage": 100.0, "present_hours": 0, "total_hours": 0}

    records = enrollment.attendance_records

    total_hours = sum(r.hours for r in records)
    if total_hours == 0:
        return {"percentage": 0.0, "present_hours": 0, "total_hours": 0}

    present_hours = sum(r.hours for r in records if r.status == "Present")

    return {
        "percentage": round((present_hours / total_hours) * 100, 2),
        "present_hours": present_hours,
        "total_hours": total_hours
    }
