from datetime import date
from sqlalchemy.orm import Session
from app.models.academic import Enrollment
from app.models.attendance import Attendance

def mark_attendance(db: Session, subject_offering_id: int, attendance_data: list[dict], attendance_date: date = None):
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
            else:
                # Create new
                records_to_insert.append(
                    Attendance(
                        enrollment_id=enrollment.id,
                        date=attendance_date,
                        status=status
                    )
                )

    if records_to_insert:
        db.add_all(records_to_insert)
        
    db.commit()
    return {"message": "Attendance marked successfully"}

def calculate_attendance_percentage(db: Session, student_id: int, subject_offering_id: int):
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.subject_offering_id == subject_offering_id
    ).first()

    if not enrollment:
        return 100.0

    records = enrollment.attendance_records

    total = len(records)
    if total == 0:
        return 100.0

    present = sum(1 for r in records if r.status == "Present")

    return round((present / total) * 100, 2)
