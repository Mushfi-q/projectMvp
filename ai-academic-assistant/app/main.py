from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.models import user, academic, assignment
from app.routers import auth, chatbot, admin, faculty, student

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],  # frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chatbot.router)
app.include_router(admin.router)
app.include_router(faculty.router)
app.include_router(student.router)

# This will create tables automatically (temporary for dev)
Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "AI Academic Assistant Backend Running"}
