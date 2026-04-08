from unittest.mock import MagicMock
from scraper import fetch_source, enrich_article


MOCK_FEED = {
    "entries": [
        {
            "title": "Student Demand Rises",
            "link": "https://pbsanews.co.uk/article-1",
            "published": "Tue, 08 Apr 2026 09:00:00 +0000",
        }
    ]
}

MOCK_ARTICLE_HTML = """
<html>
<head>
  <meta property="og:image" content="https://pbsanews.co.uk/img.jpg"/>
</head>
<body>
  <article>Full article body text here. More text about student housing.</article>
</body>
</html>
"""


def test_fetch_source_returns_articles(mocker):
    mocker.patch("feedparser.parse", return_value=MOCK_FEED)
    source = {"name": "PBSA News", "domain": "pbsanews.co.uk", "feed_url": "https://pbsanews.co.uk/feed/"}
    articles = fetch_source(source)
    assert len(articles) == 1
    assert articles[0]["headline"] == "Student Demand Rises"
    assert articles[0]["url"] == "https://pbsanews.co.uk/article-1"
    assert articles[0]["source_name"] == "PBSA News"
    assert articles[0]["source_domain"] == "pbsanews.co.uk"


def test_fetch_source_skips_entries_without_link(mocker):
    feed = {"entries": [{"title": "No link entry"}]}
    mocker.patch("feedparser.parse", return_value=feed)
    source = {"name": "PBSA News", "domain": "pbsanews.co.uk", "feed_url": "https://pbsanews.co.uk/feed/"}
    articles = fetch_source(source)
    assert articles == []


def test_enrich_article_extracts_og_image_and_body(mocker):
    mock_response = MagicMock()
    mock_response.text = MOCK_ARTICLE_HTML
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)
    article = {"url": "https://pbsanews.co.uk/article-1", "body_text": "", "thumbnail_url": None}
    enriched = enrich_article(article)
    assert enriched["thumbnail_url"] == "https://pbsanews.co.uk/img.jpg"
    assert "Full article body text" in enriched["body_text"]


def test_enrich_article_handles_missing_og_image(mocker):
    mock_response = MagicMock()
    mock_response.text = "<html><body><article>Body only.</article></body></html>"
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)
    article = {"url": "https://pbsanews.co.uk/article-1", "body_text": "", "thumbnail_url": None}
    enriched = enrich_article(article)
    assert enriched["thumbnail_url"] is None
    assert enriched["body_text"] == "Body only."


def test_enrich_article_handles_request_failure(mocker):
    import requests
    mocker.patch("requests.get", side_effect=requests.RequestException("timeout"))
    article = {"url": "https://pbsanews.co.uk/article-1", "body_text": "", "thumbnail_url": None}
    enriched = enrich_article(article)
    assert enriched["body_text"] == ""
    assert enriched["thumbnail_url"] is None
