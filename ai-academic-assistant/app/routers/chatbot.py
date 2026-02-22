from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.services.ai_service import generate_subject_response
from app.models.user import User


from app.models.academic import Student, Enrollment

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    subject_offering_id: int
    message: str


@router.post("/")
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role.lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can access chatbot")

    # Get student record
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    # Validate enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.subject_offering_id == request.subject_offering_id
    ).first()

    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this subject")

    response = generate_subject_response(
        request.subject_offering_id,
        request.message,
        student.id
    )

    return {
        "success": True,
        "data": response
    }
