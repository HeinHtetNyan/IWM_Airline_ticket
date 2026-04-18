import logging
import smtplib
import ssl
import time
from email.utils import formataddr, formatdate, make_msgid
from email.message import EmailMessage
from pathlib import Path
from socket import gaierror
from typing import Protocol

import mailtrap as mt
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_EMAIL_RETRIES = 3

_templates_dir = Path(__file__).resolve().parent.parent / "templates"
_template_env = Environment(
    loader=FileSystemLoader(str(_templates_dir)),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailBackend(Protocol):
    def send(self, *, recipient: str, subject: str, html_content: str) -> None: ...


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
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid(domain=settings.EMAIL_FROM.split("@")[-1] if "@" in (settings.EMAIL_FROM or "") else "localhost")  
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

        try:
            with smtp:
                if not settings.EMAIL_USE_SSL and settings.EMAIL_USE_TLS:
                    smtp.starttls(context=ssl_context)
                if settings.EMAIL_REQUIRE_AUTH:
                    smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
                smtp.send_message(message)
                logger.info("Successfully sent email to %s (Subject: '%s')", recipient, subject)
        except smtplib.SMTPAuthenticationError as e:
            logger.error("Failed to send email to %s: Authentication failed. Check SMTP credentials. %s", recipient, e)
            raise
        except smtplib.SMTPConnectError as e:
            logger.error("Failed to send email to %s: Could not connect to SMTP server %s:%s. %s", recipient, settings.EMAIL_HOST, settings.EMAIL_PORT, e)
            raise
        except smtplib.SMTPException as e:
            logger.error("Failed to send email to %s: SMTP error occurred: %s", recipient, e)
            raise
        except TimeoutError as e:
            logger.error("Failed to send email to %s: Connection to SMTP server %s timed out. %s", recipient, settings.EMAIL_HOST, e)
            raise
        except gaierror as e:
            logger.error("Failed to send email to %s: Could not resolve SMTP host %s. %s", recipient, settings.EMAIL_HOST, e)
            raise
        except Exception as e:
            logger.error("Failed to send email to %s: An unexpected error occurred: %s", recipient, e)
            raise


class MailtrapEmailBackend:
    @staticmethod
    def _get_sender() -> mt.Address:
        email_from = settings.EMAIL_FROM or "hello@heinh.dev"
        name = settings.EMAIL_FROM_NAME or "Mailtrap Test"
        return mt.Address(email=email_from, name=name)

    def send(self, *, recipient: str, subject: str, html_content: str) -> None:
        if not settings.EMAIL_ENABLED:
            logger.info("Email sending is disabled. Skipping message to %s", recipient)
            return

        try:
            mail = mt.Mail(
                sender=self._get_sender(),
                to=[mt.Address(email=recipient)],
                subject=subject,
                html=html_content,
                category="Integration Test",
            )
            client = mt.MailtrapClient(token=settings.MAILTRAP_API_TOKEN)
            client.send(mail)
            logger.info("Successfully sent email to %s (Subject: '%s') via Mailtrap", recipient, subject)
        except Exception as e:
            logger.error("Failed to send email to %s using Mailtrap: %s", recipient, e)
            raise


# Switch to MailtrapEmailBackend
email_backend: EmailBackend = MailtrapEmailBackend()


def render_template(template_name: str, context: dict[str, str]) -> str:
    template = _template_env.get_template(template_name)
    return template.render(**context)


def send_email(
    *, recipient: str, subject: str, template_name: str, context: dict[str, str]
) -> None:
    html_content = render_template(template_name, context)
    
    for attempt in range(1, _MAX_EMAIL_RETRIES + 1):
        try:
            email_backend.send(recipient=recipient, subject=subject, html_content=html_content)
            return
        except Exception as e:
            if attempt == _MAX_EMAIL_RETRIES:
                logger.error("Final attempt failed to send email to %s: %s", recipient, e)
                raise
            sleep_time = attempt * 2
            logger.warning("Attempt %d to send email failed for %s. Retrying in %d seconds... Error: %s", attempt, recipient, sleep_time, e)
            time.sleep(sleep_time)


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
