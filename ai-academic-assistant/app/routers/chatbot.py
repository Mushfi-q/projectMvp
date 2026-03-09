import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.services.ai_service import generate_subject_response, get_student_performance_summary, extract_reminder_payload
from app.services.nlp_service import classify_intent
from app.models.user import User
from app.models.reminder import Reminder


from app.models.academic import Student, Enrollment
from app.models.chat import ChatSession, ChatFeedback, ChatMessage

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    subject_offering_id: int
    message: str

class ChatResponse(BaseModel):
    success: bool
    data: str
    message_id: int = None
    processing_time_ms: float = None

class FeedbackRequest(BaseModel):
    message_id: int
    rating: int
    comment: str | None = None

class GenericChatResponse(BaseModel):
    success: bool
    data: str


@router.post("/", response_model=ChatResponse, summary="Send a message to the AI chatbot")
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

    # Get or create chat session
    session_record = db.query(ChatSession).filter(
        ChatSession.student_id == student.id,
        ChatSession.subject_offering_id == request.subject_offering_id
    ).first()

    if not session_record:
        session_record = ChatSession(
            student_id=student.id,
            subject_offering_id=request.subject_offering_id
        )
        db.add(session_record)
        db.commit()
        db.refresh(session_record)

    user_query = request.message
    final_prompt = user_query

    # Classify Intent via NLP Service
    intent = classify_intent(user_query)

    if intent == "reminder":
        payload = extract_reminder_payload(user_query)
        if payload and payload.get("title") and payload.get("due_date"):
            from datetime import datetime
            
            try:
                dt_obj = datetime.strptime(payload["due_date"], "%Y-%m-%d %H:%M:%S")
                
                new_reminder = Reminder(
                    student_id=student.id,
                    title=payload["title"],
                    due_date=dt_obj
                )
                db.add(new_reminder)
                db.commit()
                
                return {
                    "success": True,
                    "data": f"I've successfully set a reminder for '{payload['title']}' on {dt_obj.strftime('%b %d at %I:%M %p')}!"
                }
            except Exception as e:
                pass # Fallback to generic chat if parsing fails
        
        # If extraction failed
        return {
            "success": True,
            "data": "I understand you want to set a reminder, but I couldn't quite catch the exact date or topic. Could you format it like 'Set reminder for IoT study session today at 7pm'?"
        }

    if intent == "performance":
        summary = get_student_performance_summary(db, student.id)

        structured_context = "Student Performance Summary:\n"

        for item in summary:
            if item['subject'] == enrollment.subject_offering.subject.subject_name:
                structured_context += f"""
    Subject: {item['subject']}
    Attendance: {item['attendance']}%
    Average Marks: {item['avg_marks']}%
    Missed Assignments: {item['missed_assignments']}
    Risk Level: {item['risk_level']}
    """

        final_prompt = structured_context + "\nExplain clearly and suggest improvements based on the student's query: " + user_query
    
    import time
    start_time = time.time()
    
    response, message_id = generate_subject_response(
        request.subject_offering_id,
        final_prompt,
        student.id,
        session_record.id
    )
    
    end_time = time.time()

    return {
        "success": True,
        "data": response,
        "message_id": message_id,
        "processing_time_ms": round((end_time - start_time) * 1000, 2)
    }

@router.post("/feedback", response_model=GenericChatResponse, summary="Submit RAG generation feedback")
def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can submit chatbot feedback")

    # Upsert logic
    existing_feedback = db.query(ChatFeedback).filter(ChatFeedback.message_id == request.message_id).first()
    
    if existing_feedback:
        existing_feedback.rating = request.rating
        existing_feedback.comment = request.comment
        db.commit()
        return {"success": True, "data": "Feedback updated successfully"}
    else:
        new_feedback = ChatFeedback(
            message_id=request.message_id,
            rating=request.rating,
            comment=request.comment
        )
        db.add(new_feedback)
        db.commit()
        return {"success": True, "data": "Feedback recorded successfully"}


@router.get("/history/{subject_offering_id}", summary="Get chat history for a subject")
def get_chat_history(
    subject_offering_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can access chat history")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    session_record = db.query(ChatSession).filter(
        ChatSession.student_id == student.id,
        ChatSession.subject_offering_id == subject_offering_id
    ).first()

    if not session_record:
        return {"success": True, "data": []}

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_record.id
    ).order_by(ChatMessage.created_at.asc()).all()

    return {
        "success": True,
        "data": [
            {
                "role": m.role,
                "content": m.content,
                "message_id": m.id if m.role == "assistant" else None
            }
            for m in messages
        ]
    }
