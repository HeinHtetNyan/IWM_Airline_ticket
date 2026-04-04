import logging
import smtplib
import ssl
from email.utils import formataddr
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_templates_dir = Path(__file__).resolve().parent.parent / "templates"
_template_env = Environment(
    loader=FileSystemLoader(str(_templates_dir)),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailBackend(Protocol):
    def send(self, *, recipient: str, subject: str, html_content: str) -> None:
        ...


class SMTPEmailBackend:
    @staticmethod
    def _build_from_header() -> str:
        email_from = settings.EMAIL_FROM or settings.EMAIL_USERNAME
        if settings.EMAIL_FROM_NAME:
            return formataddr((settings.EMAIL_FROM_NAME, email_from))
        return email_from

    def send(self, *, recipient: str, subject: str, html_content: str) -> None:
        if not settings.EMAIL_ENABLED:
            logger.info("Email sending is disabled. Skipping message to %s", recipient)
            return

        message = EmailMessage()
        message["From"] = self._build_from_header()
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content("Please view this email in an HTML-compatible client.")
        message.add_alternative(html_content, subtype="html")

        if settings.EMAIL_USE_SSL and settings.EMAIL_USE_TLS:
            raise ValueError("EMAIL_USE_SSL and EMAIL_USE_TLS cannot both be enabled")

        ssl_context = ssl.create_default_context()

        if settings.EMAIL_USE_SSL:
            smtp = smtplib.SMTP_SSL(
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                timeout=settings.EMAIL_TIMEOUT_SECONDS,
                context=ssl_context,
            )
        else:
            smtp = smtplib.SMTP(
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                timeout=settings.EMAIL_TIMEOUT_SECONDS,
            )

        with smtp:
            if not settings.EMAIL_USE_SSL and settings.EMAIL_USE_TLS:
                smtp.starttls(context=ssl_context)
            if settings.EMAIL_REQUIRE_AUTH:
                smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            smtp.send_message(message)


email_backend: EmailBackend = SMTPEmailBackend()


def render_template(template_name: str, context: dict[str, str]) -> str:
    template = _template_env.get_template(template_name)
    return template.render(**context)


def send_email(*, recipient: str, subject: str, template_name: str, context: dict[str, str]) -> None:
    html_content = render_template(template_name, context)
    email_backend.send(recipient=recipient, subject=subject, html_content=html_content)


def _verification_url(token: str) -> str:
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/verify-email?token={token}"


def _reset_password_url(token: str) -> str:
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={token}"


def send_verification_email(email: str, token: str) -> None:
    try:
        send_email(
            recipient=email,
            subject="Verify your email address",
            template_name="verification_email.html",
            context={
                "action_url": _verification_url(token),
                "token": token,
            },
        )
    except Exception:
        logger.exception("Failed to send verification email to %s", email)
        raise


def send_reset_password_email(email: str, token: str) -> None:
    try:
        send_email(
            recipient=email,
            subject="Reset your password",
            template_name="reset_password_email.html",
            context={
                "action_url": _reset_password_url(token),
                "token": token,
            },
        )
    except Exception:
        logger.exception("Failed to send reset password email to %s", email)
        raise
