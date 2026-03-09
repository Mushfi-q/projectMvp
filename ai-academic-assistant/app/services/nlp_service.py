def classify_intent(query: str):
    query = query.lower()

    performance_keywords = [
        "weak", "risk", "performance",
        "how am i", "should i worry"
    ]

    deadline_keywords = [
        "deadline", "due", "upcoming",
        "this week", "assignment due"
    ]

    reminder_keywords = [
        "remind me", "set a reminder", "set reminder",
        "remind", "reminder"
    ]

    if any(k in query for k in performance_keywords):
        return "performance"

    if any(k in query for k in deadline_keywords):
        return "deadline"

    if any(k in query for k in reminder_keywords):
        return "reminder"

    return "conceptual"


def extract_entities(query: str, db=None):
    import re
    from datetime import datetime, timedelta

    entities = {
        "subject": None,
        "assignment": None,
        "date": None,
        "exam": None
    }
    
    query_lower = query.lower()
    
    # 1. Very basic Date heuristics
    if "today" in query_lower:
        entities["date"] = datetime.now().date().isoformat()
    elif "tomorrow" in query_lower:
        entities["date"] = (datetime.now() + timedelta(days=1)).date().isoformat()
        
    # 2. Exam Rules
    if "midterm" in query_lower or "mid term" in query_lower:
        entities["exam"] = "Midterm"
    elif "final" in query_lower or "end semester" in query_lower:
        entities["exam"] = "Finals"
        
    # 3. Dynamic DB mappings for precise Subject / Assignment matches
    if db:
        try:
            from app.models.academic import Subject
            from app.models.assignment import Assignment
            
            # Map subjects
            subjects = db.query(Subject).all()
            for sub in subjects:
                if sub.subject_name.lower() in query_lower or sub.subject_code.lower() in query_lower:
                    entities["subject"] = sub.subject_name
                    break
                    
            # Map assignments
            assignments = db.query(Assignment).all()
            for assign in assignments:
                if assign.title.lower() in query_lower:
                    entities["assignment"] = assign.title
                    break
        except Exception:
            pass # Failsafe if DB session drops
            
    return entities

