import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.document import Document, ProcessingStatus
from app.models.chat import ChatMessage
from app.schemas.document import DocumentResponse, DocumentDetailResponse
from app.schemas.chat import ChatMessageCreate, ChatMessageResponse
from app.tasks.tasks import summarize_document_task
from app.api.deps import get_current_user_optional, get_current_user
from app.services.document_processor import extract_text_from_file
from app.services.llm import generate_document_answer

router = APIRouter()

# Directory where uploaded files will be stored
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[any] = Depends(get_current_user_optional)
):
    """
    Upload a log/document. Guests are restricted to 3 uploads per IP.
    Registered users have unlimited uploads and their histories are persisted.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Enforce guest limit
    if not current_user:
        guest_count = db.query(Document).filter(
            Document.user_id == None,
            Document.client_ip == client_ip
        ).count()
        
        if guest_count >= 3:
            raise HTTPException(
                status_code=400,
                detail="Guest limit reached (max 3 uploads). Please login or sign up for unlimited uploads!"
            )

    # Save file locally
    file_path = os.path.join(UPLOAD_DIR, file.filename)
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
        status=ProcessingStatus.PENDING,
        user_id=current_user.id if current_user else None,
        client_ip=client_ip
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Trigger background summarization
    try:
        # Try Celery task first
        summarize_document_task.delay(db_document.id)
    except Exception as e:
        # Fallback to local FastAPI BackgroundTasks if Celery/Redis is down
        background_tasks.add_task(summarize_document_task, db_document.id)

    return db_document

@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Optional[any] = Depends(get_current_user_optional)
):
    """
    Retrieve documents. Returns personal history for logged-in users,
    or session/IP-based logs for guests.
    """
    client_ip = request.client.host if request.client else "unknown"

    if current_user:
        # Registered user sees only their documents
        documents = db.query(Document).filter(
            Document.user_id == current_user.id
        ).offset(skip).limit(limit).all()
    else:
        # Guest sees only their temporary uploads (filtered by client IP)
        documents = db.query(Document).filter(
            Document.user_id == None,
            Document.client_ip == client_ip
        ).offset(skip).limit(limit).all()
        
    return documents

@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[any] = Depends(get_current_user_optional)
):
    """
    Get details of a specific document including summaries and chat history.
    """
    client_ip = request.client.host if request.client else "unknown"
    db_document = db.query(Document).filter(Document.id == document_id).first()
    
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Verify authorization
    if db_document.user_id is not None:
        if not current_user or db_document.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
    else:
        # Guest document, verify IP matches
        if db_document.client_ip != client_ip:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
            
    return db_document

@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[any] = Depends(get_current_user_optional)
):
    """
    Delete a document and its associated summaries / chat histories.
    """
    client_ip = request.client.host if request.client else "unknown"
    db_document = db.query(Document).filter(Document.id == document_id).first()
    
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Verify authorization
    if db_document.user_id is not None:
        if not current_user or db_document.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this document")
    else:
        if db_document.client_ip != client_ip:
            raise HTTPException(status_code=403, detail="Not authorized to delete this document")
            
    # Delete file from local filesystem
    if os.path.exists(db_document.file_path):
        try:
            os.remove(db_document.file_path)
        except Exception:
            pass
            
    db.delete(db_document)
    db.commit()
    return None

@router.post("/{document_id}/chat", response_model=ChatMessageResponse)
def chat_with_document(
    document_id: int,
    chat_in: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: any = Depends(get_current_user)
):
    """
    Ask a follow-up question about the document. Only available to logged-in users.
    """
    # Fetch document and verify user ownership
    db_document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not db_document:
        raise HTTPException(
            status_code=404, 
            detail="Document not found or you do not have permission to chat with it."
        )
        
    if db_document.status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Document is still processing or has failed. You can only chat once summarization completes."
        )

    # Extract text from document file
    extracted_text = extract_text_from_file(db_document.file_path)
    if not extracted_text:
        raise HTTPException(status_code=400, detail="Cannot read document contents for Q&A.")

    # Retrieve existing chat history (format as dict array)
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in db_document.chat_messages
    ]

    # Generate answer using our LLM helper
    answer = generate_document_answer(extracted_text, chat_in.content, history)

    # Save messages to database
    user_msg = ChatMessage(
        document_id=document_id,
        role="user",
        content=chat_in.content
    )
    assistant_msg = ChatMessage(
        document_id=document_id,
        role="assistant",
        content=answer
    )
    
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg

@router.get("/{document_id}/chat", response_model=List[ChatMessageResponse])
def get_chat_history(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: any = Depends(get_current_user)
):
    """
    Retrieve follow-up chat logs for a document. Only available to logged-in users.
    """
    db_document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found or access denied")
        
    return db_document.chat_messages
