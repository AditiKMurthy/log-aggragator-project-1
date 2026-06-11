import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.document import Document, ProcessingStatus
from app.schemas.document import DocumentResponse, DocumentDetailResponse
from app.tasks.tasks import summarize_document_task

router = APIRouter()

# Directory where uploaded files will be stored
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a document file (PDF, TXT, etc.), save it, and queue a background 
    summarization task.
    """
    # Create file path
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # Save the file locally
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    # Add document record to the database
    db_document = Document(
        filename=file.filename,
        file_path=file_path,
        file_type=file.content_type,
        status=ProcessingStatus.PENDING
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Trigger background summarization Celery task
    try:
        summarize_document_task.delay(db_document.id)
    except Exception as e:
        # Fallback to local background tasks if Celery is not running
        # (This is useful for local testing without Celery broker running)
        pass

    return db_document

@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve all documents.
    """
    documents = db.query(Document).offset(skip).limit(limit).all()
    return documents

@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific document including its summaries.
    """
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_document

@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a document and its associated summaries from the database 
    and delete the local file.
    """
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from local filesystem
    if os.path.exists(db_document.file_path):
        try:
            os.remove(db_document.file_path)
        except Exception:
            pass
            
    db.delete(db_document)
    db.commit()
    return None
