import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

def _send_email_smtp(to_email: str, subject: str, body_html: str, body_text: str) -> bool:
    """Send email via SMTP with HTML and Text fallbacks."""
    # If SMTP_USER is not set, log to console for local testing convenience
    if not settings.SMTP_USER:
        logger.warning(
            f"SMTP_USER is not configured. Logging email instead:\n"
            f"TO: {to_email}\n"
            f"SUBJECT: {subject}\n"
            f"BODY:\n{body_text}\n"
        )
        # Return True so development proceeds as if the mail was sent successfully
        return True

    try:
        # Create message container
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM
        message["To"] = to_email

        # Attach text and HTML parts
        part1 = MIMEText(body_text, "plain")
        part2 = MIMEText(body_html, "html")
        message.attach(part1)
        message.attach(part2)

        # Connect to SMTP server
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.ehlo()
        if settings.SMTP_PORT == 587:
            server.starttls() # Enable security TLS
            server.ehlo()
        
        # Log in if credentials exist
        if settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        # Send email
        server.sendmail(settings.SMTP_FROM, to_email, message.as_string())
        server.quit()
        logger.info(f"Successfully sent email to {to_email} with subject '{subject}'")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email} via SMTP: {str(e)}")
        # Fallback to printing the verification info in console so developers can proceed
        logger.warning(
            f"SMTP Fallback (check config): Logging email content instead:\n"
            f"TO: {to_email}\n"
            f"SUBJECT: {subject}\n"
            f"BODY:\n{body_text}\n"
        )
        return False

def send_registration_otp_email(email: str, otp_code: str) -> bool:
    """Send registration OTP email."""
    subject = "LogStream AI - Verify Your Account Registration"
    body_text = (
        f"Welcome to LogStream AI!\n\n"
        f"Your 6-digit verification code is: {otp_code}\n"
        f"This code will expire in 10 minutes.\n\n"
        f"If you did not request this, please ignore this email."
    )
    body_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #090d16; color: #f3f4f6; padding: 24px;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #111622; border: 1px solid #232a3b; border-radius: 12px; padding: 32px; text-align: center;">
          <h2 style="color: #6366f1; margin-bottom: 24px;">LogStream AI Verification</h2>
          <p style="font-size: 16px; line-height: 1.5; color: #9ca3af;">Thank you for registering! Please use the following One-Time Password (OTP) to complete your account verification:</p>
          <div style="font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #10b981; background-color: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); padding: 12px; border-radius: 8px; margin: 24px 0; display: inline-block; min-width: 180px;">
            {otp_code}
          </div>
          <p style="font-size: 13px; color: #6b7280; margin-top: 24px;">This code will expire in 10 minutes. If you did not register for an account, please ignore this email.</p>
        </div>
      </body>
    </html>
    """
    return _send_email_smtp(email, subject, body_html, body_text)

def send_password_reset_otp_email(email: str, otp_code: str) -> bool:
    """Send password reset OTP email."""
    subject = "LogStream AI - Reset Your Account Password"
    body_text = (
        f"You requested a password reset for your LogStream AI account.\n\n"
        f"Your 6-digit password reset code is: {otp_code}\n"
        f"This code will expire in 10 minutes.\n\n"
        f"If you did not request this, please ignore this email."
    )
    body_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #090d16; color: #f3f4f6; padding: 24px;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #111622; border: 1px solid #232a3b; border-radius: 12px; padding: 32px; text-align: center;">
          <h2 style="color: #6366f1; margin-bottom: 24px;">Password Reset Request</h2>
          <p style="font-size: 16px; line-height: 1.5; color: #9ca3af;">We received a request to reset your password. Please use the following One-Time Password (OTP) to proceed with your reset:</p>
          <div style="font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #f59e0b; background-color: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.2); padding: 12px; border-radius: 8px; margin: 24px 0; display: inline-block; min-width: 180px;">
            {otp_code}
          </div>
          <p style="font-size: 13px; color: #6b7280; margin-top: 24px;">This code will expire in 10 minutes. If you did not request a password reset, please ignore this email.</p>
        </div>
      </body>
    </html>
    """
    return _send_email_smtp(email, subject, body_html, body_text)
