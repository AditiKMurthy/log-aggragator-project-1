from datetime import datetime
from pydantic import BaseModel

class ChatMessageBase(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageResponse(ChatMessageBase):
    id: int
    document_id: int
    created_at: datetime

    class Config:
        from_attributes = True
