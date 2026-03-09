from app.database import engine, Base
import app.models.user
import app.models.academic
import app.models.assignment
import app.models.attendance
import app.models.reminder
import app.models.chat

Base.metadata.create_all(bind=engine)
print("Migration complete!")
