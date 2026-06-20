import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base

class UserOTP(Base):
    __tablename__ = "user_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    purpose = Column(String, nullable=False)  # "registration" or "password_reset"
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    @property
    def is_expired(self) -> bool:
        return datetime.datetime.utcnow() > self.expires_at
