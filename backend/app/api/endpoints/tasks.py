from fastapi import APIRouter, Depends, HTTPException
from celery.result import AsyncResult
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.document import Document
from app.tasks.celery_app import celery

router = APIRouter()

@router.get("/{task_id}")
def get_task_status(task_id: str):
    """
    Get the status of an asynchronous Celery task.
    """
    task_result = AsyncResult(task_id, app=celery)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": str(task_result.result) if task_result.ready() else None
    }

@router.get("/document/{document_id}")
def get_document_processing_status(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the database-stored processing status of a document.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "document_id": document.id,
        "filename": document.filename,
        "status": document.status,
        "updated_at": document.updated_at
    }
