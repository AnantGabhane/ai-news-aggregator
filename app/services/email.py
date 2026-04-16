import os
import smtplib
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

from dotenv import load_dotenv
import markdown
import requests

load_dotenv()

RESEND_API_URL = "https://api.resend.com/emails"


def _get_email_settings() -> dict[str, str | None]:
    return {
        "provider": os.getenv("EMAIL_PROVIDER", "auto").strip().lower(),
        "recipient": os.getenv("MY_EMAIL"),
        "smtp_password": os.getenv("APP_PASSWORD"),
        "resend_api_key": os.getenv("RESEND_API_KEY"),
        "email_from": os.getenv("EMAIL_FROM"),
        "reply_to": os.getenv("EMAIL_REPLY_TO"),
    }


def _normalize_recipients(recipients: list[str] | None) -> list[str]:
    settings = _get_email_settings()
    resolved = recipients or [settings["recipient"]]
    cleaned = [email.strip() for email in resolved if email and email.strip()]
    if not cleaned:
        raise ValueError("No valid recipients provided")
    return cleaned


def _send_via_resend(
    subject: str,
    body_text: str,
    body_html: str | None,
    recipients: list[str],
    settings: dict[str, str | None],
) -> dict[str, Any]:
    api_key = settings["resend_api_key"]
    email_from = settings["email_from"]

    if not api_key:
        raise ValueError("RESEND_API_KEY environment variable is not set")
    if not email_from:
        raise ValueError("EMAIL_FROM environment variable is not set")

    payload: dict[str, Any] = {
        "from": email_from,
        "to": recipients,
        "subject": subject,
        "text": body_text,
        "html": body_html or markdown_to_html(body_text),
    }
    if settings["reply_to"]:
        payload["reply_to"] = settings["reply_to"]

    try:
        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        response_text = ""
        if exc.response is not None:
            response_text = exc.response.text.strip()
        detail = f"Resend email delivery failed: {exc}"
        if response_text:
            detail = f"{detail} | Response: {response_text}"
        raise ValueError(detail) from exc


def _send_via_smtp(
    subject: str,
    body_text: str,
    body_html: str | None,
    recipients: list[str],
    settings: dict[str, str | None],
) -> None:
    sender = settings["recipient"]
    smtp_password = settings["smtp_password"]

    if not sender:
        raise ValueError("MY_EMAIL environment variable is not set")
    if not smtp_password:
        raise ValueError("APP_PASSWORD environment variable is not set")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(body_text, "plain"))
    if body_html:
        msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, smtp_password)
            smtp.sendmail(sender, recipients, msg.as_string())
    except smtplib.SMTPException as exc:
        raise ValueError(f"SMTP email delivery failed: {exc}") from exc


def send_email(
    subject: str,
    body_text: str,
    body_html: str | None = None,
    recipients: list[str] | None = None,
):
    settings = _get_email_settings()
    resolved_recipients = _normalize_recipients(recipients)

    provider = settings["provider"]
    if provider not in {"auto", "resend", "smtp"}:
        raise ValueError(
            "EMAIL_PROVIDER must be one of: auto, resend, smtp"
        )

    if provider in {"auto", "resend"} and settings["resend_api_key"]:
        return _send_via_resend(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            recipients=resolved_recipients,
            settings=settings,
        )

    if provider in {"auto", "smtp"}:
        return _send_via_smtp(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            recipients=resolved_recipients,
            settings=settings,
        )

    raise ValueError(
        "No supported email delivery configuration found. Set RESEND_API_KEY and "
        "EMAIL_FROM for Render-friendly delivery, or APP_PASSWORD for SMTP."
    )


def markdown_to_html(markdown_text: str) -> str:
    html = markdown.markdown(markdown_text, extensions=['extra', 'nl2br'])
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
        }}
        h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 24px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 20px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        p {{
            margin: 8px 0;
            color: #4a4a4a;
        }}
        strong {{
            font-weight: 600;
            color: #1a1a1a;
        }}
        em {{
            font-style: italic;
            color: #666;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 20px 0;
        }}
        .greeting {{
            font-size: 16px;
            font-weight: 500;
            color: #1a1a1a;
            margin-bottom: 12px;
        }}
        .introduction {{
            color: #4a4a4a;
            margin-bottom: 20px;
        }}
        .article-link {{
            display: inline-block;
            margin-top: 8px;
            color: #0066cc;
            font-size: 14px;
        }}
    </style>
</head>
<body>
{html}
</body>
</html>"""


def digest_to_html(digest_response) -> str:
    from app.agent.email_agent import EmailDigestResponse
    
    if not isinstance(digest_response, EmailDigestResponse):
        return markdown_to_html(digest_response.to_markdown() if hasattr(digest_response, 'to_markdown') else str(digest_response))
    
    html_parts = []
    greeting_html = markdown.markdown(digest_response.introduction.greeting, extensions=['extra', 'nl2br'])
    introduction_html = markdown.markdown(digest_response.introduction.introduction, extensions=['extra', 'nl2br'])
    html_parts.append(f'<div class="greeting">{greeting_html}</div>')
    html_parts.append(f'<div class="introduction">{introduction_html}</div>')
    html_parts.append('<hr>')
    
    for article in digest_response.articles:
        html_parts.append(f'<h3>{html.escape(article.title)}</h3>')
        summary_html = markdown.markdown(article.summary, extensions=['extra', 'nl2br'])
        html_parts.append(f'<div>{summary_html}</div>')
        html_parts.append(f'<p><a href="{html.escape(article.url)}" class="article-link">Read more →</a></p>')
        html_parts.append('<hr>')
    
    html_content = '\n'.join(html_parts)
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
        }}
        h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 20px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        p {{
            margin: 8px 0;
            color: #4a4a4a;
        }}
        strong {{
            font-weight: 600;
            color: #1a1a1a;
        }}
        em {{
            font-style: italic;
            color: #666;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 20px 0;
        }}
        .greeting {{
            font-size: 16px;
            font-weight: 500;
            color: #1a1a1a;
            margin-bottom: 12px;
        }}
        .introduction {{
            color: #4a4a4a;
            margin-bottom: 20px;
        }}
        .article-link {{
            display: inline-block;
            margin-top: 8px;
            color: #0066cc;
            font-size: 14px;
        }}
        .greeting p {{
            margin: 0;
        }}
        .introduction p {{
            margin: 0;
        }}
        div {{
            margin: 8px 0;
            color: #4a4a4a;
        }}
        div p {{
            margin: 4px 0;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""


def send_email_to_self(subject: str, body: str):
    recipient = _get_email_settings()["recipient"]
    if not recipient:
        raise ValueError("MY_EMAIL environment variable is not set. Please set it in your .env file.")
    send_email(subject, body, recipients=[recipient])


if __name__ == "__main__":
    send_email_to_self("Test from Python", "Hello from my script.")
