
import os
import smtplib
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_validator import validate_email, EmailNotValidError

def notify_user(
    to_email: str,
    sender_override: Optional[str] = None,
    password_override: Optional[str] = None
) -> bool:
    """
    Send a registration notification email.

    Environment variables used (if overrides not provided):
      EMAIL_ADDRESS  -> sender email (e.g. "you@example.com")
      EMAIL_PASSWORD -> sender's SMTP password (app password if using Gmail + 2FA)

    Returns True on success, False on failure.
    """

    # Validate recipient email
    try:
        validated_recipient = validate_email(to_email).email
    except EmailNotValidError as e:
        print("Invalid recipient email:", e)
        return False

    # Get sender and password from overrides or environment variables
    sender = sender_override or os.environ.get("EMAIL_ADDRESS")
    password = password_override or os.environ.get("EMAIL_PASSWORD")

    if not sender:
        print("EMAIL_ADDRESS environment variable not set and no sender_override provided. Aborting send.")
        return False
    if not password:
        print("EMAIL_PASSWORD environment variable not set and no password_override provided. Aborting send.")
        return False

    # Validate sender email too
    try:
        validated_sender = validate_email(sender).email
    except EmailNotValidError as e:
        print("Invalid sender email:", e)
        return False

    subject = "Registration successful"
    body = "User registered successfully. Now you can login to access the features."

    msg = MIMEMultipart()
    msg["From"] = validated_sender
    msg["To"] = validated_recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # Using Gmail SMTP with STARTTLS (port 587)
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(validated_sender, password)
            server.send_message(msg)
        print("Email sent successfully to", validated_recipient)
        return True
    except smtplib.SMTPAuthenticationError as e:
        print("SMTP authentication failed:", e)
    except smtplib.SMTPException as e:
        print("SMTP error occurred:", e)
    except Exception as e:
        print("Failed to send email:", e)
    return False


if __name__ == "__main__":
    # Example usage:
    # 1) Preferred: set env vars beforehand and just call notify_user("recipient@example.com")
    # 2) For local testing only: pass sender_override and password_override (DO NOT commit these)
    #
    # Example (local-only):
    notify_user("sahanakgowda268@gmail.com",
                sender_override=os.getenv("EMAIL_ADDRESS"),
                password_override=os.getenv("EMAIL_PASSWORD"))

    success = notify_user("sahanakgowda268@gmail.com")
    if not success:
        print("Send failed.")
