import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.models import user, academic, assignment, attendance
from app.routers import auth, chatbot, admin, faculty, student

app = FastAPI()

# Serve static files (CSS)
app.mount("/static", StaticFiles(directory="app/frontend"), name="static")

origins = [
    "http://127.0.0.1:8080",
    "http://localhost:8080",
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

# Dashboard route serves the unified Phase 4 index.html
@app.get("/app")
def serve_dashboard():
    return FileResponse("app/frontend/index.html")

@app.get("/faculty")
def serve_faculty():
    return FileResponse("app/frontend/faculty.html")

@app.get("/admin")
def serve_admin():
    return FileResponse("app/frontend/admin.html")
