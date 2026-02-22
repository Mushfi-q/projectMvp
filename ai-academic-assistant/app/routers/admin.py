import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.services.rag_service import build_index
from app.models.assignment import Document

UPLOAD_PATH = "uploaded_pdfs"
os.makedirs(UPLOAD_PATH, exist_ok=True)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/upload-pdf")
def upload_pdf(
    subject_offering_id: int,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admin can upload PDFs")

    file_path = os.path.join(UPLOAD_PATH, file.filename)

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    # Build FAISS index
    build_index(subject_offering_id, file_path)

    # Save document record
    document = Document(
        subject_offering_id=subject_offering_id,
        title=file.filename,
        file_url=file_path,
        document_type="Syllabus",
        uploaded_by=current_user.id
    )

    db.add(document)
    db.commit()

    return {
        "success": True,
        "data": "PDF uploaded and indexed successfully"
    }
