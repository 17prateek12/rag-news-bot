import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib

from app.config import settings

logger = logging.getLogger(__name__)


def _send_email_sync(to_email: str, subject: str, text_body: str, html_body: str) -> bool:
    username = settings.smtp_mail_username
    password = settings.smtp_mail_password
    from_email = settings.effective_from_email or username

    if not username or not password:
        logger.warning(
            "SMTP credentials not configured (SMTP_MAIL_USERNAME / SMTP_MAIL_PASSWORD). "
            "Skipping actual email dispatch. Reset recipient: %s",
            to_email,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Context Agent <{from_email}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.sendmail(from_email, [to_email], msg.as_string())
        logger.info("Password reset email sent successfully to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send email via SMTP to %s: %s", to_email, exc)
        return False


class EmailService:
    @classmethod
    async def send_password_reset_email(cls, to_email: str, reset_url: str) -> bool:
        subject = "Reset Your Context Agent Password"
        text_body = f"""Hello,

We received a request to reset your password for Context Agent.

Click or paste the link below to set a new password:
{reset_url}

This link is valid for 15 minutes. If you did not request this reset, please ignore this email.

Best regards,
Context Agent Team
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #1e293b;
      background-color: #f8fafc;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 540px;
      margin: 30px auto;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 32px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    .header {{
      display: flex;
      align-items: center;
      margin-bottom: 24px;
    }}
    .brand {{
      font-size: 20px;
      font-weight: 700;
      color: #0f172a;
    }}
    .btn {{
      display: inline-block;
      background-color: #2563eb;
      color: #ffffff !important;
      text-decoration: none;
      padding: 12px 24px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 15px;
      margin: 20px 0;
    }}
    .footer {{
      margin-top: 32px;
      padding-top: 16px;
      border-top: 1px solid #e2e8f0;
      font-size: 12px;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="brand">Context Agent</div>
    </div>
    <h2>Password Reset Request</h2>
    <p>Hello,</p>
    <p>We received a request to reset your password for your Context Agent account. Click the button below to choose a new password:</p>
    <div>
      <a href="{reset_url}" class="btn" target="_blank">Reset Password</a>
    </div>
    <p style="font-size: 13px; color: #64748b;">
      Or copy and paste this link into your browser:<br>
      <a href="{reset_url}" style="color: #2563eb; word-break: break-all;">{reset_url}</a>
    </p>
    <p style="font-size: 13px; color: #64748b;">This link is valid for <strong>15 minutes</strong>. If you did not request a password reset, you can safely ignore this email.</p>
    <div class="footer">
      &copy; Context Agent. All rights reserved.
    </div>
  </div>
</body>
</html>
"""
        return await asyncio.to_thread(_send_email_sync, to_email, subject, text_body, html_body)

    @classmethod
    async def send_daily_digest_notification(
        cls, to_email: str, topics: list[str], app_url: str
    ) -> bool:
        subject = "Your Daily Topic Briefs are Ready (Context Agent)"
        topics_text = "\n".join(f"  • {topic}" for topic in topics)
        text_body = f"""Hello,

Your daily intelligence briefs have been updated for your subscribed topics:

{topics_text}

Click the link below to view today's summaries and source articles on Context Agent:
{app_url}

Best regards,
Context Agent Team
"""

        topics_html = "".join(
            f'<li style="margin-bottom: 6px; color: #0f172a; font-weight: 500;">{topic}</li>'
            for topic in topics
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #1e293b;
      background-color: #f8fafc;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 540px;
      margin: 30px auto;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 32px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    .header {{
      display: flex;
      align-items: center;
      margin-bottom: 24px;
    }}
    .brand {{
      font-size: 20px;
      font-weight: 700;
      color: #0f172a;
    }}
    .topics-box {{
      background: #f1f5f9;
      border-radius: 8px;
      padding: 16px 20px;
      margin: 20px 0;
    }}
    .topics-box ul {{
      margin: 8px 0 0 0;
      padding-left: 20px;
    }}
    .btn {{
      display: inline-block;
      background-color: #2563eb;
      color: #ffffff !important;
      text-decoration: none;
      padding: 12px 24px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 15px;
      margin: 20px 0;
    }}
    .footer {{
      margin-top: 32px;
      padding-top: 16px;
      border-top: 1px solid #e2e8f0;
      font-size: 12px;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="brand">Context Agent</div>
    </div>
    <h2>Today's Intelligence Briefs are Ready</h2>
    <p>Hello,</p>
    <p>Fresh news has arrived and our AI analyst has synthesized daily intelligence summaries for your active topic watches:</p>
    <div class="topics-box">
      <strong>Your Watched Topics:</strong>
      <ul>
        {topics_html}
      </ul>
    </div>
    <div>
      <a href="{app_url}" class="btn" target="_blank">View Today's Briefs</a>
    </div>
    <p style="font-size: 13px; color: #64748b;">
      Or visit Context Agent directly: <a href="{app_url}" style="color: #2563eb;">{app_url}</a>
    </p>
    <div class="footer">
      &copy; Context Agent. All rights reserved.
    </div>
  </div>
</body>
</html>
"""
        return await asyncio.to_thread(_send_email_sync, to_email, subject, text_body, html_body)
