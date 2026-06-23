import pytest
from app.models.user import User
from app.models.otp import UserOTP

def test_register_new_user(client, db):
    # Register new user
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "securepassword"}
    )
    assert response.status_code == 201
    assert "Verification OTP sent" in response.json()["message"]
    
    # Assert user created in db and inactive
    user = db.query(User).filter(User.email == "newuser@example.com").first()
    assert user is not None
    assert user.is_active is False

def test_register_duplicate_user(client, db):
    # Setup: Create active user
    active_user = User(email="active@example.com", hashed_password="hashed_pw", is_active=True)
    db.add(active_user)
    db.commit()

    # Attempt to register with duplicate email
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "active@example.com", "password": "password123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered."

def test_verify_registration_flow(client, db):
    # Register
    client.post(
        "/api/v1/auth/register",
        json={"email": "verify@example.com", "password": "securepassword"}
    )
    
    # Retrieve OTP from database
    db_otp = db.query(UserOTP).filter(UserOTP.email == "verify@example.com").first()
    assert db_otp is not None
    
    # Verify with wrong OTP
    response = client.post(
        "/api/v1/auth/verify-registration",
        json={"email": "verify@example.com", "otp_code": "000000"}
    )
    assert response.status_code == 400
    
    # Verify with correct OTP
    response = client.post(
        "/api/v1/auth/verify-registration",
        json={"email": "verify@example.com", "otp_code": db_otp.otp_code}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["email"] == "verify@example.com"
    
    # Verify user is active in db
    user = db.query(User).filter(User.email == "verify@example.com").first()
    assert user.is_active is True

def test_login_flow(client, db):
    # Setup: Register and activate a user
    client.post(
        "/api/v1/auth/register",
        json={"email": "loginuser@example.com", "password": "mypassword"}
    )
    db_otp = db.query(UserOTP).filter(UserOTP.email == "loginuser@example.com").first()
    client.post(
        "/api/v1/auth/verify-registration",
        json={"email": "loginuser@example.com", "otp_code": db_otp.otp_code}
    )
    
    # Try incorrect password
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 400
    
    # Try correct password
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@example.com", "password": "mypassword"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_password_reset_flow(client, db):
    # Setup: Create active user
    client.post(
        "/api/v1/auth/register",
        json={"email": "reset@example.com", "password": "oldpassword"}
    )
    db_otp = db.query(UserOTP).filter(UserOTP.email == "reset@example.com").first()
    client.post(
        "/api/v1/auth/verify-registration",
        json={"email": "reset@example.com", "otp_code": db_otp.otp_code}
    )
    
    # Request password reset
    response = client.post(
        "/api/v1/auth/password-reset-request",
        json={"email": "reset@example.com"}
    )
    assert response.status_code == 200
    
    # Retrieve reset OTP from database
    reset_otp = db.query(UserOTP).filter(
        UserOTP.email == "reset@example.com",
        UserOTP.purpose == "password_reset"
    ).first()
    assert reset_otp is not None
    
    # Confirm password reset
    response = client.post(
        "/api/v1/auth/password-reset-confirm",
        json={
            "email": "reset@example.com",
            "otp_code": reset_otp.otp_code,
            "new_password": "newpassword123"
        }
    )
    assert response.status_code == 200
    
    # Login with new password
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "newpassword123"}
    )
    assert response.status_code == 200
