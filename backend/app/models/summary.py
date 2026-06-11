import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    summary_text = Column(Text, nullable=False)
    key_points = Column(Text, nullable=True)  # Store as JSON string or plain text list
    
    # Note: If pgvector is installed, you can add:
    # from pgvector.sqlalchemy import Vector
    # embedding = Column(Vector(1536))  # e.g., OpenAI text-embedding-3-small dimensions
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="summaries")
