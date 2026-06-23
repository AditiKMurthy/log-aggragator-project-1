from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

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

    model_config = ConfigDict(from_attributes=True)

class SummaryResponse(SummaryInDBBase):
    pass
