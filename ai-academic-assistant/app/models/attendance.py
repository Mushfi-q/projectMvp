from sqlalchemy import Column, Integer, Date, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False)  # Present / Absent
    hours = Column(Integer, default=1)

    enrollment = relationship("Enrollment", back_populates="attendance_records")
