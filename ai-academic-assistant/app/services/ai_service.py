import ollama
from app.services.rag_service import retrieve_chunks
from datetime import datetime, timedelta
from app.models.assignment import Assignment, InternalMark
from app.models.academic import Enrollment
from app.database import SessionLocal
from app.utils.logger import logger


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


def generate_subject_response(subject_offering_id, query, student_id=None):
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

    # Retrieve study material
    retrieved_chunks = retrieve_chunks(subject_offering_id, query)

    # Get structured data via helpers
    deadline_info = get_deadline_data(db, subject_offering_id)
    performance_info = get_performance_data(db, subject_offering_id, student_id)

    context = "\n\n".join(retrieved_chunks) if retrieved_chunks else ""

    context_section = context if is_conceptual else ""
    assignment_section = deadline_info if is_deadline_query else ""
    performance_section = performance_info if is_performance_query else ""

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

Question:
{query}

Provide clear and concise guidance.
If question relates to study material, answer using context.
If related to preparation or priority, consider deadlines.
Answer clearly.
"""

    try:
        response = ollama.chat(
            model="phi3:mini",
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 300, "num_ctx": 2048}
        )
        content = response["message"]["content"]
    except Exception as e:
        logger.error(f"Ollama chat generation failed: {str(e)}")
        content = "AI service temporarily unavailable."

    db.close()
    return content
