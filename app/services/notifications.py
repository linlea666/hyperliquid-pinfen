import json
from typing import List, Optional

import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import session_scope
from app.models import (
    NotificationHistory,
    NotificationSubscription,
    NotificationTemplate,
)

logger = logging.getLogger(__name__)


def list_templates() -> List[NotificationTemplate]:
    with session_scope() as session:
        return session.execute(select(NotificationTemplate).order_by(NotificationTemplate.created_at)).scalars().all()


def create_template(name: str, channel: str, subject: Optional[str], content: str, description: Optional[str]) -> NotificationTemplate:
    with session_scope() as session:
        tpl = NotificationTemplate(
            name=name,
            channel=channel,
            subject=subject,
            content=content,
            description=description,
        )
        session.add(tpl)
        session.flush()
        session.refresh(tpl)
        return tpl


def subscribe(recipient: str, template_id: int, enabled: bool = True) -> NotificationSubscription:
    with session_scope() as session:
        sub = NotificationSubscription(recipient=recipient, template_id=template_id, enabled=1 if enabled else 0)
        session.add(sub)
        session.flush()
        session.refresh(sub)
        return sub


def list_subscriptions(template_id: Optional[int] = None) -> List[NotificationSubscription]:
    with session_scope() as session:
        stmt = select(NotificationSubscription).order_by(NotificationSubscription.created_at.desc())
        if template_id:
            stmt = stmt.where(NotificationSubscription.template_id == template_id)
        return session.execute(stmt).scalars().all()


def send_notification(template_id: int, recipient: str, payload: Optional[dict] = None) -> NotificationHistory:
    settings = get_settings()
    with session_scope() as session:
        template = session.get(NotificationTemplate, template_id)
        if not template:
            raise ValueError("Template not found")
        channel = template.channel or "email"
        history = NotificationHistory(
            template_id=template_id,
            recipient=recipient,
            channel=channel,
            status="pending",
            attempts=0,
            payload=json.dumps(payload) if payload else None,
        )
        session.add(history)
        session.flush()
        try:
            if channel == "email":
                _send_email(settings, template, recipient, payload or {})
            elif channel == "webhook":
                _send_webhook(settings, template, recipient, payload or {})
            history.status = "sent"
        except Exception as exc:
            history.status = "failed"
            history.error = str(exc)
            logger.error("Notification send failed", exc_info=True)
        finally:
            history.attempts += 1
            session.add(history)
            session.flush()
            session.refresh(history)
            return history


def _render_template(template: NotificationTemplate, payload: dict, field: str = "content") -> str:
    content = (template.subject or "") if field == "subject" else template.content
    for key, value in payload.items():
        content = content.replace(f"{{{{{key}}}}}", str(value))
    return content


def _send_email(settings, template: NotificationTemplate, recipient: str, payload: dict):
    import smtplib

    body = _render_template(template, payload, "content")
    subject_value = _render_template(template, payload, "subject") if template.subject else template.name
    message = f"From: {settings.smtp_from}\r\nTo: {recipient}\r\nSubject: {subject_value}\r\n\r\n{body}"

    use_ssl = settings.smtp_port == 465
    if use_ssl:
        smtp = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10.0)
    else:
        smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10.0)
        if settings.smtp_use_tls:
            smtp.starttls()
    if settings.smtp_username:
        smtp.login(settings.smtp_username, settings.smtp_password)
    smtp.sendmail(settings.smtp_from, [recipient], message)
    smtp.quit()

def _send_webhook(settings, template: NotificationTemplate, recipient: str, payload: dict):
    import httpx

    url = settings.webhook_url or recipient
    if not url:
        raise ValueError("Webhook url missing")
    body = {
        "template": template.name,
        "recipient": recipient,
        "payload": payload,
        "content": _render_template(template, payload),
    }
    resp = httpx.post(url, json=body, timeout=5.0)
    resp.raise_for_status()


def list_history(limit: int = 50) -> List[NotificationHistory]:
    with session_scope() as session:
        stmt = select(NotificationHistory).order_by(NotificationHistory.created_at.desc()).limit(limit)
        return session.execute(stmt).scalars().all()
