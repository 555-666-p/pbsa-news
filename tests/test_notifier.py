import logging
from unittest.mock import MagicMock
from notifier import send_digest

NEW_ARTICLES = [
    {
        "url": "https://pbsanews.co.uk/article-1",
        "source_name": "PBSA News",
        "source_domain": "pbsanews.co.uk",
        "headline": "New Article",
        "date": "2026-04-08",
        "thumbnail_url": None,
        "summary": "A short summary.",
        "body_text": "Body text.",
    }
]

CONFIG = {
    "api_key": "fake-brevo-key",
    "sender_address": "digest@example.com",
    "sender_name": "PBSA Digest",
    "recipients": ["user@example.com"],
    "subject": "PBSA News Digest -- {date}",
}


def test_send_digest_calls_brevo_api(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 201
    send_digest(NEW_ARTICLES, config=CONFIG, today="2026-04-08")
    mock_post.assert_called_once()
    assert mock_post.call_args[1]["headers"]["api-key"] == "fake-brevo-key"


def test_send_digest_includes_headline_in_body(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 201
    send_digest(NEW_ARTICLES, config=CONFIG, today="2026-04-08")
    payload = mock_post.call_args[1]["json"]
    assert "New Article" in payload["htmlContent"]


def test_send_digest_with_no_articles_still_sends(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 201
    send_digest([], config=CONFIG, today="2026-04-08")
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert "no new articles" in payload["htmlContent"].lower()


def test_send_digest_uses_correct_subject(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 201
    send_digest(NEW_ARTICLES, config=CONFIG, today="2026-04-08")
    payload = mock_post.call_args[1]["json"]
    assert payload["subject"] == "PBSA News Digest -- 2026-04-08"


def test_send_digest_logs_warning_on_failure(mocker, caplog):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 400
    mock_post.return_value.text = "Bad request"
    with caplog.at_level(logging.WARNING):
        send_digest(NEW_ARTICLES, config=CONFIG, today="2026-04-08")
    assert "Brevo" in caplog.text
