import pytest
import os
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db

# Use a local SQLite file for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop tables after test completes
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test.db"):
            try:
                os.remove("./test.db")
            except PermissionError:
                pass

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock external APIs: LLM (Gemini / OpenAI) and Email (SMTP)"""
    with patch("app.services.email.smtplib.SMTP") as mock_smtp, \
         patch("google.genai.Client") as mock_gemini, \
         patch("openai.OpenAI") as mock_openai:
         
        # Set up default mock behavior for Gemini
        mock_client_gemini = mock_gemini.return_value
        mock_response = mock_client_gemini.models.generate_content.return_value
        mock_response.text = '{"summary": "Test document summary from mock.", "key_points": ["- Key point 1", "- Key point 2"]}'
        
        # Set up default mock behavior for OpenAI
        mock_client = mock_openai.return_value
        mock_chat = mock_client.chat.completions.create.return_value
        mock_chat.choices = [
            type("Choice", (object,), {
                "message": type("Message", (object,), {
                    "content": '{"summary": "Test document summary from mock.", "key_points": ["- Key point 1", "- Key point 2"]}'
                })
            })
        ]
        
        yield {
            "smtp": mock_smtp,
            "gemini_model": mock_client_gemini,
            "openai_client": mock_client
        }
