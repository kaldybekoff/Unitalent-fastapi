import asyncio

from fastapi_mail import MessageSchema, MessageType

from src.celery_app import celery_app
from src.config import settings
from src.email.config import fastmail


def _send(subject: str, recipients: list[str], template: str, body: dict) -> None:
    """Synchronous wrapper to send an email from a Celery worker."""
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        template_body=body,
        subtype=MessageType.html,
    )
    asyncio.run(fastmail.send_message(message, template_name=template))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_confirmation_email(self, user_id: int, email: str, token: str) -> None:
    """Send email verification link to the user."""
    try:
        url = f"{settings.frontend_url}/auth/verify-email/{token}"
        _send(
            subject="Confirm your UniTalent account",
            recipients=[email],
            template="email_confirmation.html",
            body={"username": email, "confirmation_url": url},
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, user_id: int, email: str, token: str) -> None:
    """Send password reset link to the user."""
    try:
        url = f"{settings.frontend_url}/auth/reset-password/{token}"
        _send(
            subject="Reset your UniTalent password",
            recipients=[email],
            template="password_reset.html",
            body={"username": email, "reset_url": url},
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_application_status_email(
    self,
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    company_name: str,
    new_status: str,
) -> None:
    """Notify candidate when their application status changes."""
    try:
        _send(
            subject=f"Application update: {new_status.upper()} — {job_title}",
            recipients=[candidate_email],
            template="application_status.html",
            body={
                "candidate_name": candidate_name,
                "job_title": job_title,
                "company_name": company_name,
                "new_status": new_status,
            },
        )
    except Exception as exc:
        raise self.retry(exc=exc)
