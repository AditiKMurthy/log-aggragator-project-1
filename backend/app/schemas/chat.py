from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ChatMessageBase(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageResponse(ChatMessageBase):
    id: int
    document_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
