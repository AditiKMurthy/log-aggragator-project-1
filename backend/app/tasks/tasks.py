import logging
from app.tasks.celery_app import celery
from app.core.database import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.models.summary import Summary
from app.services.document_processor import extract_text_from_file
from app.services.llm import generate_document_summary

logger = logging.getLogger(__name__)

@celery.task(name="app.tasks.tasks.summarize_document_task")
def summarize_document_task(document_id: int):
    """
    Background Celery task to process an uploaded document:
    1. Parse and extract text content from the file.
    2. Call the AI service to summarize the content and extract key points.
    3. Save the results to the database and update document processing status.
    """
    db = SessionLocal()
    try:
        # 1. Fetch document from database
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document with ID {document_id} not found.")
            return False

        # 2. Update status to PROCESSING
        document.status = ProcessingStatus.PROCESSING
        db.commit()

        # 3. Extract text content from document file
        logger.info(f"Extracting text from {document.filename} (Path: {document.file_path})...")
        extracted_text = extract_text_from_file(document.file_path)
        if not extracted_text:
            raise ValueError("Extracted text is empty or document processing failed.")

        # 4. Generate summary using LLM service
        logger.info(f"Generating summary for document {document_id}...")
        llm_response = generate_document_summary(extracted_text)
        
        summary_text = llm_response.get("summary", "No summary generated.")
        key_points = llm_response.get("key_points", "")

        # 5. Create summary database record
        db_summary = Summary(
            document_id=document.id,
            summary_text=summary_text,
            key_points=key_points
        )
        db.add(db_summary)

        # 6. Mark document as COMPLETED
        document.status = ProcessingStatus.COMPLETED
        db.commit()
        logger.info(f"Successfully processed document {document_id}.")
        return True

    except Exception as e:
        logger.exception(f"Error processing document {document_id}: {str(e)}")
        # If anything fails, set status to FAILED
        db.rollback()
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = ProcessingStatus.FAILED
            db.commit()
        return False
        
    finally:
        db.close()
