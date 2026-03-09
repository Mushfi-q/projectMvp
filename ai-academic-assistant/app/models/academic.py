from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    start_year = Column(Integer)
    end_year = Column(Integer)


class Semester(Base):
    __tablename__ = "semesters"

    id = Column(Integer, primary_key=True, index=True)
    semester_number = Column(Integer)
    batch_id = Column(Integer, ForeignKey("batches.id"))
    academic_year = Column(String)
    is_active = Column(Integer, default=1)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    register_number = Column(String)
    batch_id = Column(Integer, ForeignKey("batches.id"))
    section = Column(String)
    current_semester_id = Column(Integer, ForeignKey("semesters.id"))

    enrollments = relationship("Enrollment", back_populates="student")
    semester_history = relationship("StudentSemesterHistory", back_populates="student")
    reminders = relationship("Reminder", back_populates="student")

class StudentSemesterHistory(Base):
    __tablename__ = "student_semester_history"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    average_attendance = Column(Integer, nullable=True) # %
    average_marks = Column(Integer, nullable=True) # %
    total_missed_assignments = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="semester_history")


class Faculty(Base):
    __tablename__ = "faculties"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    department_id = Column(Integer, ForeignKey("departments.id"))
    designation = Column(String)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    subject_name = Column(String)
    subject_code = Column(String)
    department_id = Column(Integer, ForeignKey("departments.id"))


class SubjectOffering(Base):
    __tablename__ = "subject_offerings"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    semester_id = Column(Integer, ForeignKey("semesters.id"))
    faculty_id = Column(Integer, ForeignKey("faculties.id"))

    subject = relationship("Subject")
    enrollments = relationship("Enrollment", back_populates="subject_offering")

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_offering_id = Column(Integer, ForeignKey("subject_offerings.id"), nullable=False)
    enrollment_date = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="enrollments")
    subject_offering = relationship("SubjectOffering", back_populates="enrollments")
    attendance_records = relationship("Attendance", back_populates="enrollment")
