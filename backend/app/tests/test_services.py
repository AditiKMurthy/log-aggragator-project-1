import os
import json
import pytest
from unittest.mock import patch
from app.services.document_processor import extract_text_from_file
from app.services.llm import generate_document_summary, generate_document_answer, format_key_points
from app.services.email import send_registration_otp_email, send_password_reset_otp_email

# ----------------- Document Processor Tests -----------------

def test_extract_text_from_txt_file(tmp_path):
    test_file = tmp_path / "test.txt"
    content = "Hello, this is a log text."
    test_file.write_text(content, encoding="utf-8")
    
    extracted = extract_text_from_file(str(test_file))
    assert extracted == content

def test_extract_text_nonexistent_file():
    extracted = extract_text_from_file("nonexistent_file.log")
    assert extracted == ""

# ----------------- LLM Services Tests -----------------

def test_format_key_points_list():
    points = ["Point one", "Point two"]
    formatted = format_key_points(points)
    assert formatted == "- Point one\n- Point two"

def test_format_key_points_string_list():
    points = '["Point one", "Point two"]'
    formatted = format_key_points(points)
    assert formatted == "- Point one\n- Point two"

def test_format_key_points_plain_string():
    points = "Simple statement without bullet"
    formatted = format_key_points(points)
    assert formatted == "- Simple statement without bullet"

@patch("app.core.config.settings.GEMINI_API_KEY", "mock_key")
def test_generate_document_summary_gemini(mock_external_services):
    res = generate_document_summary("Document content to summarize.")
    assert "summary" in res
    assert "key_points" in res
    assert "mock" in res["summary"]

@patch("app.core.config.settings.GEMINI_API_KEY", "")
@patch("app.core.config.settings.OPENAI_API_KEY", "")
def test_generate_document_summary_fallback_mock():
    # If no keys are set, it should return mock fallback response
    res = generate_document_summary("Document content.")
    assert "placeholder summary generated locally" in res["summary"]

@patch("app.core.config.settings.GEMINI_API_KEY", "")
@patch("app.core.config.settings.OPENAI_API_KEY", "")
def test_generate_document_answer_offline_fallback():
    # When no keys are set, it should use keyword matching sentences fallback
    doc_text = "ERROR: Connection failed at database node.\nINFO: Retry successful."
    answer = generate_document_answer(doc_text, "What caused the error?")
    assert "Offline Fallback Answer" in answer
    assert "ERROR: Connection failed" in answer

# ----------------- Email Service Tests -----------------

@patch("app.services.email.settings.SMTP_USER", "test@gmail.com")
@patch("app.services.email.settings.SMTP_PASSWORD", "secret")
def test_send_registration_otp_mock(mock_external_services):
    success = send_registration_otp_email("user@example.com", "123456")
    assert success is True
    # Verify SMTP was called
    assert mock_external_services["smtp"].called

@patch("app.services.email.settings.SMTP_USER", "")
def test_send_otp_console_fallback():
    # If SMTP settings are missing, email.py prints to console and returns True
    success = send_registration_otp_email("user@example.com", "123456")
    assert success is True
