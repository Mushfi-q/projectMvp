from groq import Groq
from app.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)
from app.services.rag_service import retrieve_chunks
from app.services.attendance_service import calculate_attendance_percentage
from datetime import datetime, timedelta
from app.models.assignment import Assignment, InternalMark, Submission
from app.models.academic import Enrollment, SubjectOffering
from app.models.chat import ChatMessage
from app.database import SessionLocal
from app.utils.logger import logger

_response_cache = {}

def calculate_risk(attendance_pct, avg_marks_pct, missed_assignments):
    score = 0

    if isinstance(attendance_pct, (int, float)) and attendance_pct < 75:
        score += 1
    if isinstance(avg_marks_pct, (int, float)) and avg_marks_pct < 50:
        score += 1
    if missed_assignments >= 2:
        score += 1

    if score == 0:
        level = "Safe"
    elif score == 1:
        level = "Mild"
    elif score == 2:
        level = "Moderate"
    else:
        level = "High"

    return score, level

def count_missed_assignments(db, student_id, subject_offering_id):
    # Get all assignments for subject
    assignments = db.query(Assignment).filter(
        Assignment.subject_offering_id == subject_offering_id
    ).all()

    if not assignments:
        return 0

    missed = 0

    for assignment in assignments:
        submission = db.query(Submission).filter(
            Submission.assignment_id == assignment.id,
            Submission.student_id == student_id
        ).first()

        if not submission:
            missed += 1

    return missed

def calculate_average_marks(db, student_id, subject_offering_id):
    marks = db.query(InternalMark).filter(
        InternalMark.student_id == student_id,
        InternalMark.subject_offering_id == subject_offering_id
    ).all()

    if not marks:
        return "No exams recorded yet"

    total_obtained = sum(m.marks_obtained for m in marks)
    total_max = sum(m.max_marks for m in marks)

    if total_max == 0:
        return "No exams recorded yet"

    return round((total_obtained / total_max) * 100, 2)


def get_student_performance_summary(db, student_id):
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student_id
    ).all()

    summary = []

    for enrollment in enrollments:
        if not enrollment.subject_offering or not enrollment.subject_offering.subject:
            continue
            
        subject = enrollment.subject_offering.subject.subject_name
        subject_offering_id = enrollment.subject_offering.id

        attendance_pct = calculate_attendance_percentage(
            db, student_id, subject_offering_id
        )

        avg_marks_pct = calculate_average_marks(
            db, student_id, subject_offering_id
        )

        missed = count_missed_assignments(
            db, student_id, subject_offering_id
        )

        score, level = calculate_risk(
            attendance_pct, avg_marks_pct, missed
        )

        summary.append({
            "subject": subject,
            "attendance": attendance_pct,
            "avg_marks": avg_marks_pct,
            "missed_assignments": missed,
            "risk_level": level
        })

    return summary


def _is_conceptual_query(query_lower):
    return any(word in query_lower for word in [
        "define", "what is", "explain", "describe"
    ])

def _is_deadline_query(query_lower):
    return any(word in query_lower for word in [
        "urgent", "deadline", "due", "assignment",
        "study first", "priority", "what should i study"
    ])

def _is_performance_query(query_lower):
    return any(word in query_lower for word in [
        "weak", "performance", "marks", "score"
    ])


def get_deadline_data(db, subject_offering_id):
    upcoming_assignments = db.query(Assignment).filter(
        Assignment.subject_offering_id == subject_offering_id,
        Assignment.deadline >= datetime.utcnow()
    ).all()

    if not upcoming_assignments:
        return "No upcoming assignments."

    deadline_info = ""
    for a in upcoming_assignments:
        days_left = (a.deadline - datetime.utcnow()).days
        if days_left <= 3:
            deadline_info += f"\nURGENT: '{a.title}' due in {days_left} days."
        else:
            deadline_info += f"\nUpcoming: '{a.title}' due in {days_left} days."
    return deadline_info


def get_performance_data(db, subject_offering_id, student_id):
    performance_info = ""
    if student_id:
        marks = db.query(InternalMark).filter(
            InternalMark.subject_offering_id == subject_offering_id,
            InternalMark.student_id == student_id
        ).all()

        if not marks:
            return "No exams recorded yet."

        for m in marks:
            if m.max_marks > 0:
                percentage = (m.marks_obtained / m.max_marks) * 100
                performance_info += f"""
PERFORMANCE_DATA_START
MARKS_OBTAINED={m.marks_obtained}
MAX_MARKS={m.max_marks}
PERCENTAGE={percentage:.2f}
WEAK_THRESHOLD=50
PERFORMANCE_DATA_END
"""
    return performance_info


def generate_subject_response(subject_offering_id, query, student_id=None, session_id=None):
    db = SessionLocal()

    query_lower = query.lower()

    is_conceptual = any(word in query_lower for word in [
        "define", "what is", "explain", "describe"
    ])

    is_deadline_query = any(word in query_lower for word in [
        "urgent", "deadline", "due", "assignment",
        "study first", "priority", "what should i study"
    ])

    is_performance_query = any(word in query_lower for word in [
        "weak", "performance", "marks", "score"
    ])

    # Detect greetings/casual — skip RAG retrieval for these
    greeting_words = ["hi", "hello", "hey", "good morning", "good evening", "thanks", "thank you", "bye", "ok", "okay"]
    is_greeting = query_lower.strip().rstrip("!.") in greeting_words or len(query_lower.strip()) <= 3

    print("QUERY:", query)
    print("SUBJECT OFFERING ID:", subject_offering_id)

    # Resolve subject_id from subject_offering for FAISS lookup
    from app.models.academic import SubjectOffering
    subject_offering = db.query(SubjectOffering).filter(SubjectOffering.id == subject_offering_id).first()
    subject_id = subject_offering.subject_id if subject_offering else subject_offering_id
    print("RESOLVED SUBJECT ID:", subject_id)

    # Retrieve study material only for actual academic queries
    if is_greeting:
        retrieved_chunks = []
    else:
        retrieved_chunks = retrieve_chunks(subject_id, query)

    print("RETRIEVED CHUNKS:", len(retrieved_chunks))

    # Fast-Path Caching for identical recent queries (bypasses LLM payload entirely)
    cache_key = f"{subject_offering_id}_{query_lower}_{student_id}"
    if cache_key in _response_cache:
        final_answer, cached_msg_id = _response_cache[cache_key]
        message_id = cached_msg_id
        if session_id:
            user_msg = ChatMessage(session_id=session_id, role="user", content=query)
            assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=final_answer)
            db.add(user_msg)
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
            message_id = assistant_msg.id
            
            # Re-cache with the new DB ID
            _response_cache[cache_key] = (final_answer, message_id)
            
        db.close()
        return final_answer, message_id

    # Get structured data via helpers
    deadline_info = get_deadline_data(db, subject_offering_id)
    performance_info = get_performance_data(db, subject_offering_id, student_id)

    context = "\n\n".join(retrieved_chunks) if retrieved_chunks else ""

    context_section = context if is_conceptual else ""
    assignment_section = deadline_info if is_deadline_query else ""
    performance_section = performance_info if is_performance_query else ""

    # Fetch last 5 messages for memory
    chat_history_text = ""
    if session_id:
        history = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(5).all()
        
        if history:
            history.reverse()
            chat_history_text = "Recent Conversation History:\n"
            for msg in history:
                role_label = "Student" if msg.role == "user" else "Assistant"
                chat_history_text += f"{role_label}: {msg.content}\n"

    # --- Token Length Limiter & Context Trimming ---
    if len(context_section) > 2000:
        context_section = context_section[:2000] + "\n... [TRUNCATED]"
        
    if len(chat_history_text) > 1000:
        chat_history_text = "Recent Conversation History:\n... [TRUNCATED]\n" + chat_history_text[-1000:]

    prompt = f"""
    You are an academic assistant.

    Follow these strict rules:
    - Only use the provided Context and Assignments Info.
    - Do NOT invent assignment names.
    - Do NOT add information not present in the system.
    - If no data exists, say so clearly.
    - Only use the information provided.
    - If PERFORMANCE_DATA_START is present:
      - Compare PERCENTAGE with WEAK_THRESHOLD.
      - If PERCENTAGE < WEAK_THRESHOLD, say: "You are weak in this subject based on current marks."
      - If not, say: "Your performance is above the weak threshold."
      - Do not reinterpret numbers.

    Study Material:
    {context_section}

    Assignments Info:
    {assignment_section}

    Performance Info:
    {performance_section}

    {chat_history_text}

    Question:
    {query}

    Provide clear and concise guidance.
    If question relates to study material, answer using context.
    If related to preparation or priority, consider deadlines.
    Answer clearly.
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Updated to a supported Groq model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        final_answer = response.choices[0].message.content

        # Save the interaction to memory
        message_id = None
        if session_id:
            user_msg = ChatMessage(session_id=session_id, role="user", content=query)
            assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=final_answer)
            db.add(user_msg)
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
            message_id = assistant_msg.id

        # Cache the successful generation
        _response_cache[cache_key] = (final_answer, message_id)
        
        # Prevent memory leak by keeping cache small manually
        if len(_response_cache) > 100:
            _response_cache.clear()

        db.close()
        return final_answer, message_id
    except Exception as e:
        logger.error(f"Groq chat generation failed: {str(e)}")
        db.close()
        return "AI service temporarily unavailable.", None


def extract_reminder_payload(query: str):
    """
    Uses LLM to extract a structured JSON reminder payload from natural language.
    Expects format: { "title": "...", "due_date": "YYYY-MM-DD HH:MM:SS" } 
    If time isn't specified, defaults to 09:00:00 of the target date.
    Returns parsed dictionary or None.
    """
    import json
    
    prompt = f"""
    You are an AI extracting reminder details from a user's message.
    The current date/time is roughly: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    User message: "{query}"

    Extract the event title and the exact date/time. 
    Return strictly raw JSON format, nothing else. No markdown blocks.
    Format required:
    {{
      "title": "Extracted title",
      "due_date": "YYYY-MM-DD HH:MM:SS"
    }}

    If you cannot decipher a date, return the JSON with due_date as null.
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        raw_json = response.choices[0].message.content.strip()
        # Remove potential markdown wrappers if LLM still includes them
        if raw_json.startswith("```json"):
            raw_json = raw_json[7:-3].strip()
        return json.loads(raw_json)
    except Exception as e:
        logger.error(f"Reminder payload extraction failed: {str(e)}")
        return None

