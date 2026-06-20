from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.document import ProcessingStatus

class DocumentBase(BaseModel):
    filename: str
    file_type: Optional[str] = None

class DocumentCreate(DocumentBase):
    file_path: str

class DocumentUpdate(BaseModel):
    status: Optional[ProcessingStatus] = None

class DocumentInDBBase(DocumentBase):
    id: int
    user_id: Optional[int] = None
    client_ip: Optional[str] = None
    status: ProcessingStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentResponse(DocumentInDBBase):
    pass

class DocumentDetailResponse(DocumentInDBBase):
    summaries: List["SummaryResponse"] = []
    chat_messages: List["ChatMessageResponse"] = []

from app.schemas.summary import SummaryResponse
from app.schemas.chat import ChatMessageResponse
DocumentDetailResponse.model_rebuild()
