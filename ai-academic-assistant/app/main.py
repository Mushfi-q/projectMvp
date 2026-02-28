import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.models import user, academic, assignment
from app.routers import auth, chatbot, admin, faculty, student

app = FastAPI()

# Serve static files (CSS)
app.mount("/static", StaticFiles(directory="app/frontend"), name="static")

origins = [
    "http://127.0.0.1:5500",  # if using Live Server
    "http://localhost:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

# Root route serves login page
@app.get("/")
def serve_login():
    return FileResponse("app/frontend/login.html")

@app.get("/student")
def serve_student():
    return FileResponse("app/frontend/student.html")

@app.get("/faculty")
def serve_faculty():
    return FileResponse("app/frontend/faculty.html")
