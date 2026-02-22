from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    subject_offering_id = Column(Integer, ForeignKey("subject_offerings.id"))
    title = Column(String)
    description = Column(Text)
    deadline = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    file_url = Column(String)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    marks = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)


class InternalMark(Base):
    __tablename__ = "internal_marks"

    id = Column(Integer, primary_key=True, index=True)
    subject_offering_id = Column(Integer, ForeignKey("subject_offerings.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    marks_obtained = Column(Integer)
    max_marks = Column(Integer)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    subject_offering_id = Column(Integer, ForeignKey("subject_offerings.id"))
    title = Column(String)
    file_url = Column(String)
    document_type = Column(String)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    chunk_text = Column(Text)
    embedding_vector = Column(Text)  # store serialized vector
    chunk_index = Column(Integer)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)  # User / Assistant
    message_text = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
