from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class SummaryBase(BaseModel):
    summary_text: str
    key_points: Optional[str] = None

class SummaryCreate(SummaryBase):
    document_id: int

class SummaryUpdate(SummaryBase):
    pass

class SummaryInDBBase(SummaryBase):
    id: int
    document_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SummaryResponse(SummaryInDBBase):
    pass
