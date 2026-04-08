import logging
import requests

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

ARTICLE_ROW = """
<tr>
  <td style="padding:12px;border-bottom:1px solid #eee;">
    <div style="font-size:11px;color:#888;margin-bottom:4px;">{source_name} &middot; {date}</div>
    <div style="font-weight:700;color:#1a3a5c;font-size:15px;margin-bottom:6px;">
      <a href="{url}" style="color:#1a3a5c;text-decoration:none;">{headline}</a>
    </div>
    <div style="font-size:13px;color:#555;">{summary}</div>
    <a href="{url}" style="font-size:12px;color:#2563eb;">Read full article</a>
  </td>
</tr>"""

NO_ARTICLES_ROW = """
<tr><td style="padding:24px;text-align:center;color:#888;">
  No new articles found today. Check back tomorrow.
</td></tr>"""

EMAIL_TEMPLATE = """
<html><body style="font-family:-apple-system,sans-serif;background:#f4f6f8;padding:24px;">
<div style="max-width:640px;margin:0 auto;">
  <div style="background:#1a3a5c;color:white;padding:16px 20px;border-radius:8px 8px 0 0;">
    <h1 style="margin:0;font-size:20px;">PBSA News Digest</h1>
    <p style="margin:4px 0 0;font-size:13px;opacity:0.8;">{date}</p>
  </div>
  <div style="background:white;border-radius:0 0 8px 8px;border:1px solid #e0e0e0;">
    <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
  </div>
  <p style="text-align:center;font-size:11px;color:#aaa;margin-top:16px;">
    PBSA News Digest &middot; Powered by Google Gemini
  </p>
</div>
</body></html>"""


def send_digest(articles: list[dict], config: dict, today: str) -> None:
    rows = "".join(
        ARTICLE_ROW.format(
            source_name=a["source_name"],
            date=a["date"],
            url=a["url"],
            headline=a["headline"],
            summary=a.get("summary") or a.get("body_text", "")[:200],
        )
        for a in articles
    ) or NO_ARTICLES_ROW

    html_content = EMAIL_TEMPLATE.format(date=today, rows=rows)
    subject = config["subject"].format(date=today)

    payload = {
        "sender": {"name": config["sender_name"], "email": config["sender_address"]},
        "to": [{"email": r} for r in config["recipients"]],
        "subject": subject,
        "htmlContent": html_content,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": config["api_key"],
    }
    response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=15)
    if response.status_code not in (200, 201):
        logging.warning("Brevo API error %s: %s", response.status_code, response.text)
