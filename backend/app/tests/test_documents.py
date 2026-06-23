import pytest
import io
from unittest.mock import patch, MagicMock
from app.models.user import User
from app.models.document import Document, ProcessingStatus
from app.models.summary import Summary

@pytest.fixture
def auth_header(client, db):
    # Register and activate a test user
    client.post(
        "/api/v1/auth/register",
        json={"email": "docowner@example.com", "password": "password123"}
    )
    user_otp = db.query(UserOTP).filter(UserOTP.email == "docowner@example.com").first()
    res = client.post(
        "/api/v1/auth/verify-registration",
        json={"email": "docowner@example.com", "otp_code": user_otp.otp_code}
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# Import UserOTP here for auth_header setup helper
from app.models.otp import UserOTP

@patch("app.api.endpoints.documents.summarize_document_task")
def test_guest_upload_limit(mock_task, client, db):
    # Mock celery task .delay to avoid hitting Redis
    mock_task.delay = MagicMock()
    
    # Upload 3 files successfully as guest (client IP testclient by default in test client)
    for i in range(3):
        file_data = {"file": (f"test_{i}.log", io.BytesIO(b"Log content " + str(i).encode()))}
        response = client.post("/api/v1/documents/upload", files=file_data)
        assert response.status_code == 201
        assert response.json()["status"] == "pending"

    # 4th upload should be blocked under guest mode limits
    file_data = {"file": ("test_4.log", io.BytesIO(b"4th log"))}
    response = client.post("/api/v1/documents/upload", files=file_data)
    assert response.status_code == 400
    assert "Guest limit reached" in response.json()["detail"]

@patch("app.api.endpoints.documents.summarize_document_task")
def test_registered_user_upload(mock_task, client, auth_header, db):
    mock_task.delay = MagicMock()
    
    # Upload file with authorization headers
    file_data = {"file": ("auth_test.log", io.BytesIO(b"Authorized log content"))}
    response = client.post("/api/v1/documents/upload", files=file_data, headers=auth_header)
    assert response.status_code == 201
    
    # Assert document is owned by the registered user
    doc = db.query(Document).filter(Document.filename == "auth_test.log").first()
    assert doc is not None
    assert doc.user_id is not None

def test_list_documents(client, db, auth_header):
    # Create an owned document
    user = db.query(User).filter(User.email == "docowner@example.com").first()
    user_doc = Document(filename="user_doc.log", file_path="uploads/user_doc.log", user_id=user.id)
    guest_doc = Document(filename="guest_doc.log", file_path="uploads/guest_doc.log", client_ip="testclient")
    db.add(user_doc)
    db.add(guest_doc)
    db.commit()
    
    # Guest lists documents (should see only guest_doc)
    guest_res = client.get("/api/v1/documents/")
    assert guest_res.status_code == 200
    guest_filenames = [doc["filename"] for doc in guest_res.json()]
    assert "guest_doc.log" in guest_filenames
    assert "user_doc.log" not in guest_filenames
    
    # Registered user lists documents (should see only user_doc)
    user_res = client.get("/api/v1/documents/", headers=auth_header)
    assert user_res.status_code == 200
    user_filenames = [doc["filename"] for doc in user_res.json()]
    assert "user_doc.log" in user_filenames
    assert "guest_doc.log" not in user_filenames

def test_delete_document(client, db, auth_header):
    user = db.query(User).filter(User.email == "docowner@example.com").first()
    doc = Document(filename="delete_me.log", file_path="uploads/delete_me.log", user_id=user.id)
    db.add(doc)
    db.commit()
    
    # Attempt delete without auth headers (forbidden for owned document)
    res = client.delete(f"/api/v1/documents/{doc.id}")
    assert res.status_code == 403
    
    # Delete with auth headers
    res = client.delete(f"/api/v1/documents/{doc.id}", headers=auth_header)
    assert res.status_code == 204
    
    # Assert deleted from DB
    assert db.query(Document).filter(Document.id == doc.id).first() is None

@patch("app.api.endpoints.documents.extract_text_from_file")
def test_chat_with_document_locked_for_guests(mock_extractor, client, db):
    doc = Document(filename="chat_guest.log", file_path="uploads/chat_guest.log", client_ip="testclient", status=ProcessingStatus.COMPLETED)
    db.add(doc)
    db.commit()
    
    response = client.post(f"/api/v1/documents/{doc.id}/chat", json={"content": "What is the error?"})
    # Guest mode is forbidden for chat
    assert response.status_code == 401

@patch("app.api.endpoints.documents.extract_text_from_file")
def test_chat_with_document_registered(mock_extractor, client, auth_header, db):
    mock_extractor.return_value = "ERROR: connection timeout"
    
    user = db.query(User).filter(User.email == "docowner@example.com").first()
    doc = Document(filename="chat_auth.log", file_path="uploads/chat_auth.log", user_id=user.id, status=ProcessingStatus.COMPLETED)
    db.add(doc)
    db.commit()
    
    response = client.post(
        f"/api/v1/documents/{doc.id}/chat",
        json={"content": "What is the error?"},
        headers=auth_header
    )
    assert response.status_code == 200
    assert "content" in response.json()
    assert response.json()["role"] == "assistant"
