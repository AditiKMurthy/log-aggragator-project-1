import random
import datetime
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.otp import UserOTP
from app.schemas.auth import (
    UserRegister,
    OTPVerify,
    UserLogin,
    GoogleLogin,
    PasswordResetRequest,
    PasswordResetConfirm,
    TokenResponse,
)
from app.core.security import get_password_hash, verify_password, create_access_token
from app.services.email import send_registration_otp_email, send_password_reset_otp_email

router = APIRouter()
logger = logging.getLogger(__name__)

def generate_otp() -> str:
    """Generate a 6-digit numeric string OTP."""
    return str(random.randint(100000, 999999))

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user in inactive state and send an email verification OTP.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        if existing_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered."
            )
        else:
            # User exists but is not active. Update their password and resend OTP
            existing_user.hashed_password = get_password_hash(user_in.password)
            db.commit()
            user = existing_user
    else:
        # Create inactive user
        user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            is_active=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Generate OTP
    otp_code = generate_otp()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

    # Remove any existing registration OTPs for this email
    db.query(UserOTP).filter(
        UserOTP.email == user.email,
        UserOTP.purpose == "registration"
    ).delete()

    # Save OTP to database
    db_otp = UserOTP(
        email=user.email,
        otp_code=otp_code,
        purpose="registration",
        expires_at=expires_at
    )
    db.add(db_otp)
    db.commit()

    # Send verification email
    sent = send_registration_otp_email(user.email, otp_code)
    if not sent:
        logger.error(f"Failed to send registration OTP email to {user.email}")
        # Note: In development we log to console and return success anyway

    return {"message": "Verification OTP sent to your email. Please verify to activate account."}

@router.post("/verify-registration", response_model=TokenResponse)
def verify_registration(verify_in: OTPVerify, db: Session = Depends(get_db)):
    """
    Verify the registration OTP to activate the user account.
    """
    # Fetch OTP from database
    db_otp = db.query(UserOTP).filter(
        UserOTP.email == verify_in.email,
        UserOTP.otp_code == verify_in.otp_code,
        UserOTP.purpose == "registration"
    ).first()

    if not db_otp or db_otp.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code."
        )

    # Fetch inactive user
    user = db.query(User).filter(User.email == verify_in.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Activate user
    user.is_active = True
    db.delete(db_otp) # Clean up OTP
    db.commit()
    db.refresh(user)

    # Generate login token
    access_token = create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": user.email
    }

@router.post("/login", response_model=TokenResponse)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate email and password and return a JWT access token.
    """
    user = db.query(User).filter(User.email == login_in.email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password, or account is not verified."
        )
    
    # Check if Google-only user
    if user.hashed_password is None and user.is_google_user:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is registered via Google OAuth. Please sign in with Google."
        )

    if not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password."
        )

    access_token = create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": user.email
    }

@router.post("/google", response_model=TokenResponse)
async def google_login(google_in: GoogleLogin, db: Session = Depends(get_db)):
    """
    Authenticate via Google OAuth ID token, automatically registering a new user if needed.
    """
    # Verify the ID Token with Google API
    try:
        async with httpx.AsyncClient() as client:
            # Query Google's tokeninfo endpoint to validate the JWT ID token securely
            resp = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={google_in.id_token}"
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Google ID token."
                )
            
            google_data = resp.json()
            email = google_data.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email not verified or missing in Google credentials."
                )
    except Exception as e:
        logger.error(f"Google ID token verification request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to contact Google OAuth servers."
        )

    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if user:
        # User exists, link Google status if not already set
        if not user.is_google_user:
            user.is_google_user = True
        if not user.is_active:
            user.is_active = True
        db.commit()
    else:
        # Create new Google OAuth user; password is set to None
        user = User(
            email=email,
            hashed_password=None,
            is_active=True,
            is_google_user=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": user.email
    }

@router.post("/password-reset-request")
def password_reset_request(request_in: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Initiate password reset by sending an OTP email to registered conventional users.
    """
    user = db.query(User).filter(User.email == request_in.email).first()
    
    # Silently return success to avoid user enumeration if user doesn't exist
    if not user or not user.is_active:
        return {"message": "If the email is registered, a password reset code has been sent."}

    # Verify user has a password (not Google-only)
    if user.hashed_password is None and user.is_google_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is registered via Google OAuth. Please sign in with Google."
        )

    otp_code = generate_otp()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

    # Clear old reset OTPs
    db.query(UserOTP).filter(
        UserOTP.email == user.email,
        UserOTP.purpose == "password_reset"
    ).delete()

    db_otp = UserOTP(
        email=user.email,
        otp_code=otp_code,
        purpose="password_reset",
        expires_at=expires_at
    )
    db.add(db_otp)
    db.commit()

    send_password_reset_otp_email(user.email, otp_code)
    return {"message": "If the email is registered, a password reset code has been sent."}

@router.post("/password-reset-confirm")
def password_reset_confirm(confirm_in: PasswordResetConfirm, db: Session = Depends(get_db)):
    """
    Confirm password reset using OTP verification code and update hashed password.
    """
    db_otp = db.query(UserOTP).filter(
        UserOTP.email == confirm_in.email,
        UserOTP.otp_code == confirm_in.otp_code,
        UserOTP.purpose == "password_reset"
    ).first()

    if not db_otp or db_otp.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset code."
        )

    user = db.query(User).filter(User.email == confirm_in.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Update password
    user.hashed_password = get_password_hash(confirm_in.new_password)
    db.delete(db_otp) # Clean up OTP
    db.commit()

    return {"message": "Password has been successfully updated. You can now log in."}
