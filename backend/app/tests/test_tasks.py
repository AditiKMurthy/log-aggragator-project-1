import pytest
from unittest.mock import patch
from app.models.document import Document, ProcessingStatus
from app.models.summary import Summary
from app.tasks.tasks import summarize_document_task

def test_summarize_document_task_success(db, mock_external_services):
    # Setup: Create doc in database
    doc = Document(filename="task_test.log", file_path="uploads/task_test.log", status=ProcessingStatus.PENDING)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    doc_id = doc.id
    
    # Mock database session used inside summarize_document_task
    with patch("app.tasks.tasks.SessionLocal", return_value=db), \
         patch("app.tasks.tasks.extract_text_from_file", return_value="ERROR: timeout at connection") as mock_extract:
         
        # Execute Celery task directly in sync execution mode
        result = summarize_document_task(doc_id)
        assert result is True
        
        # Verify status changed to COMPLETED using a new session
        from app.tests.conftest import TestingSessionLocal
        new_session = TestingSessionLocal()
        try:
            updated_doc = new_session.query(Document).filter(Document.id == doc_id).first()
            assert updated_doc.status == ProcessingStatus.COMPLETED
            
            # Verify Summary record was generated and has formatted key points
            summary = new_session.query(Summary).filter(Summary.document_id == doc_id).first()
            assert summary is not None
            assert "Test document summary from mock." in summary.summary_text
            assert "- Key point 1" in summary.key_points
        finally:
            new_session.close()

def test_summarize_document_task_failure(db):
    doc = Document(filename="failed_task.log", file_path="uploads/failed_task.log", status=ProcessingStatus.PENDING)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    doc_id = doc.id
    
    # Mock text extraction failure (empty text returns)
    with patch("app.tasks.tasks.SessionLocal", return_value=db), \
         patch("app.tasks.tasks.extract_text_from_file", return_value=""):
         
        result = summarize_document_task(doc_id)
        assert result is False
        
        # Verify status is set to FAILED using a new session
        from app.tests.conftest import TestingSessionLocal
        new_session = TestingSessionLocal()
        try:
            updated_doc = new_session.query(Document).filter(Document.id == doc_id).first()
            assert updated_doc.status == ProcessingStatus.FAILED
        finally:
            new_session.close()
