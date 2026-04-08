import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone


def fetch_source(source: dict) -> list[dict]:
    """Parse RSS feed for a source. Returns list of article dicts without body/thumbnail."""
    feed = feedparser.parse(source["feed_url"])
    articles = []
    for entry in feed.get("entries", []):
        url = entry.get("link")
        if not url:
            continue
        articles.append({
            "url": url,
            "source_name": source["name"],
            "source_domain": source["domain"],
            "headline": entry.get("title", "").strip(),
            "date": _parse_date(entry.get("published", "")),
            "thumbnail_url": None,
            "body_text": "",
            "summary": "",
            "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return articles


def enrich_article(article: dict) -> dict:
    """Fetch article page to extract og:image and body text. Returns updated article dict."""
    try:
        response = requests.get(
            article["url"], timeout=10, headers={"User-Agent": "PBSA-Digest/1.0"}
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            article["thumbnail_url"] = og_image["content"]

        body_tag = soup.find("article") or soup.find("main") or soup.find("body")
        if body_tag:
            article["body_text"] = body_tag.get_text(separator=" ", strip=True)[:3000]
    except requests.RequestException:
        pass
    return article


def _parse_date(date_str: str) -> str:
    """Parse RSS date string to YYYY-MM-DD. Returns today on failure."""
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
