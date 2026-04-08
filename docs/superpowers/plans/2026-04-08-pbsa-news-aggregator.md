# PBSA News Aggregator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily Python pipeline that scrapes PBSA news sources, summarises articles with Gemini, and publishes an accumulating archive to GitHub Pages with an RSS feed and Brevo email digest.

**Architecture:** A GitHub Actions cron job runs `main.py` daily at 7am. It scrapes configured RSS feeds, summarises new articles via Gemini Flash, appends them to `data/articles.json`, generates `output/index.html` and `output/feed.xml`, sends a Brevo email digest, then commits the updated data file and deploys the output to GitHub Pages.

**Tech Stack:** Python 3.11, feedparser, requests, beautifulsoup4, google-generativeai, pytest, pytest-mock, GitHub Actions, GitHub Pages, Brevo REST API

---

## File Map

| File | Responsibility |
|---|---|
| `sources.py` | Config: source RSS URLs, email recipients, sender details |
| `store.py` | Load/save `data/articles.json`; dedup by URL |
| `scraper.py` | Fetch RSS feeds; enrich each article with og:image + body text |
| `summariser.py` | Call Gemini Flash API; return summary or fallback |
| `renderer.py` | Write `output/index.html` and `output/feed.xml` from article list |
| `notifier.py` | Send HTML digest email via Brevo REST API |
| `main.py` | Orchestrate the full pipeline |
| `tests/test_store.py` | Tests for store load/save/dedup |
| `tests/test_scraper.py` | Tests for scraper with mocked HTTP |
| `tests/test_summariser.py` | Tests for summariser with mocked Gemini |
| `tests/test_renderer.py` | Tests for HTML and RSS output |
| `tests/test_notifier.py` | Tests for email send with mocked Brevo |
| `.github/workflows/daily.yml` | GitHub Actions: daily cron, run pipeline, deploy |
| `requirements.txt` | Python dependencies |
| `data/articles.json` | Persistent article store (committed to repo) |
| `output/` | Generated files (deployed to gh-pages, not committed to main) |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `sources.py`
- Create: `data/articles.json`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
feedparser==6.0.11
requests==2.31.0
beautifulsoup4==4.12.3
google-generativeai==0.7.2
pytest==8.2.0
pytest-mock==3.14.0
```

- [ ] **Step 2: Create sources.py**

```python
SOURCES = [
    {
        "name": "PBSA News",
        "domain": "pbsanews.co.uk",
        "feed_url": "https://www.pbsanews.co.uk/feed/",
    },
    # Add further sources here. Each entry needs:
    #   name      -- display name shown on cards
    #   domain    -- used for attribution label
    #   feed_url  -- RSS/Atom feed URL for the source
]

EMAIL_RECIPIENTS = [
    # Add recipient email addresses here, e.g. "colleague@thedotgroup.com"
]

EMAIL_SENDER_ADDRESS = "digest@yourdomain.com"   # must be a verified sender in Brevo
EMAIL_SENDER_NAME = "PBSA News Digest"
EMAIL_SUBJECT = "PBSA News Digest -- {date}"     # {date} replaced at send time
```

- [ ] **Step 3: Create empty article store and test package**

```bash
mkdir -p data output tests
echo '[]' > data/articles.json
touch output/.gitkeep
touch tests/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt sources.py data/articles.json output/.gitkeep tests/__init__.py
git commit -m "feat: project setup -- dependencies, config, empty store"
```

---

## Task 2: Article Store

**Files:**
- Create: `store.py`
- Create: `tests/test_store.py`

An article is a dict with keys: `url`, `source_name`, `source_domain`, `headline`, `date`, `thumbnail_url`, `body_text`, `summary`, `scraped_at`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_store.py
import pytest
from pathlib import Path
from store import load_store, save_store, add_articles


@pytest.fixture
def tmp_store(tmp_path):
    store_path = tmp_path / "articles.json"
    store_path.write_text("[]")
    return store_path


def test_load_empty_store(tmp_store):
    articles = load_store(tmp_store)
    assert articles == []


def test_save_and_reload(tmp_store):
    article = {
        "url": "https://pbsanews.co.uk/article-1",
        "source_name": "PBSA News",
        "source_domain": "pbsanews.co.uk",
        "headline": "Test headline",
        "date": "2026-04-08",
        "thumbnail_url": "https://pbsanews.co.uk/img.jpg",
        "body_text": "Body text here.",
        "summary": "Short summary.",
        "scraped_at": "2026-04-08T07:00:00Z",
    }
    save_store([article], tmp_store)
    loaded = load_store(tmp_store)
    assert len(loaded) == 1
    assert loaded[0]["url"] == article["url"]


def test_add_articles_deduplicates_by_url(tmp_store):
    existing = [{"url": "https://pbsanews.co.uk/article-1", "headline": "Old"}]
    new_articles = [
        {"url": "https://pbsanews.co.uk/article-1", "headline": "Duplicate"},
        {"url": "https://pbsanews.co.uk/article-2", "headline": "New"},
    ]
    merged = add_articles(existing, new_articles)
    assert len(merged) == 2
    assert merged[0]["headline"] == "Old"
    assert merged[1]["url"] == "https://pbsanews.co.uk/article-2"


def test_add_articles_returns_only_new(tmp_store):
    existing = [{"url": "https://pbsanews.co.uk/article-1", "headline": "Old"}]
    new_articles = [
        {"url": "https://pbsanews.co.uk/article-1", "headline": "Dup"},
        {"url": "https://pbsanews.co.uk/article-2", "headline": "New"},
    ]
    _, newly_added = add_articles(existing, new_articles, return_new=True)
    assert len(newly_added) == 1
    assert newly_added[0]["url"] == "https://pbsanews.co.uk/article-2"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_store.py -v
```
Expected: `ModuleNotFoundError: No module named 'store'`

- [ ] **Step 3: Implement store.py**

```python
# store.py
import json
from pathlib import Path
from typing import Union


def load_store(path: Union[str, Path] = "data/articles.json") -> list[dict]:
    return json.loads(Path(path).read_text())


def save_store(articles: list[dict], path: Union[str, Path] = "data/articles.json") -> None:
    Path(path).write_text(json.dumps(articles, indent=2, ensure_ascii=False))


def add_articles(
    existing: list[dict],
    new: list[dict],
    return_new: bool = False,
) -> Union[list[dict], tuple[list[dict], list[dict]]]:
    existing_urls = {a["url"] for a in existing}
    newly_added = [a for a in new if a["url"] not in existing_urls]
    merged = existing + newly_added
    if return_new:
        return merged, newly_added
    return merged
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_store.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add store.py tests/test_store.py
git commit -m "feat: article store with load/save/dedup"
```

---

## Task 3: Scraper

**Files:**
- Create: `scraper.py`
- Create: `tests/test_scraper.py`

Parses each source RSS feed via feedparser, then fetches each article page to extract `og:image` and body text.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scraper.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scraper.py -v
```
Expected: `ModuleNotFoundError: No module named 'scraper'`

- [ ] **Step 3: Implement scraper.py**

```python
# scraper.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scraper.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: RSS scraper with article page enrichment"
```

---

## Task 4: Summariser

**Files:**
- Create: `summariser.py`
- Create: `tests/test_summariser.py`

Calls Gemini Flash for a 1-2 sentence summary. Falls back to the first 200 chars of body text on failure.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_summariser.py
from unittest.mock import MagicMock
from summariser import summarise_article


def _make_article(body_text="Full article body about student housing demand."):
    return {
        "url": "https://pbsanews.co.uk/article-1",
        "headline": "Student Demand Rises",
        "body_text": body_text,
        "summary": "",
    }


def test_summarise_returns_gemini_response(mocker):
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = "Demand for PBSA rose 12% this year."
    mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)
    mocker.patch("google.generativeai.configure")
    result = summarise_article(_make_article(), api_key="fake-key")
    assert result["summary"] == "Demand for PBSA rose 12% this year."


def test_summarise_falls_back_on_api_error(mocker):
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("API error")
    mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)
    mocker.patch("google.generativeai.configure")
    result = summarise_article(_make_article(body_text="A" * 300), api_key="fake-key")
    assert result["summary"] == "A" * 200


def test_summarise_skips_article_with_empty_body(mocker):
    mocker.patch("google.generativeai.configure")
    mock_model = MagicMock()
    mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)
    result = summarise_article(_make_article(body_text=""), api_key="fake-key")
    mock_model.generate_content.assert_not_called()
    assert result["summary"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_summariser.py -v
```
Expected: `ModuleNotFoundError: No module named 'summariser'`

- [ ] **Step 3: Implement summariser.py**

```python
# summariser.py
import google.generativeai as genai

PROMPT_TEMPLATE = (
    "Summarise the following news article in 1-2 sentences. "
    "Focus on the single most important point. Write in plain English.\n\n"
    "Headline: {headline}\n\n"
    "Article:\n{body}"
)


def summarise_article(article: dict, api_key: str) -> dict:
    """Add a 'summary' field to the article dict. Returns the updated dict."""
    if not article.get("body_text"):
        return article
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = PROMPT_TEMPLATE.format(
            headline=article["headline"],
            body=article["body_text"][:2000],
        )
        response = model.generate_content(prompt)
        article["summary"] = response.text.strip()
    except Exception:
        article["summary"] = article["body_text"][:200]
    return article
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_summariser.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add summariser.py tests/test_summariser.py
git commit -m "feat: Gemini Flash summariser with fallback"
```

---

## Task 5: HTML and RSS Renderer

**Files:**
- Create: `renderer.py`
- Create: `tests/test_renderer.py`

Generates `output/index.html` (card feed, newest-first) and `output/feed.xml` (RSS 2.0).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_renderer.py
import xml.etree.ElementTree as ET
from pathlib import Path
from renderer import render_html, render_rss

SAMPLE_ARTICLES = [
    {
        "url": "https://pbsanews.co.uk/article-2",
        "source_name": "PBSA News",
        "source_domain": "pbsanews.co.uk",
        "headline": "Newer Article",
        "date": "2026-04-08",
        "thumbnail_url": "https://pbsanews.co.uk/img2.jpg",
        "body_text": "Body of newer article.",
        "summary": "Summary of newer article.",
        "scraped_at": "2026-04-08T07:00:00Z",
    },
    {
        "url": "https://pbsanews.co.uk/article-1",
        "source_name": "PBSA News",
        "source_domain": "pbsanews.co.uk",
        "headline": "Older Article",
        "date": "2026-04-07",
        "thumbnail_url": None,
        "body_text": "Body of older article.",
        "summary": "Summary of older article.",
        "scraped_at": "2026-04-07T07:00:00Z",
    },
]


def test_render_html_contains_headlines(tmp_path):
    out = tmp_path / "index.html"
    render_html(SAMPLE_ARTICLES, output_path=out)
    content = out.read_text()
    assert "Newer Article" in content
    assert "Older Article" in content


def test_render_html_contains_summaries(tmp_path):
    out = tmp_path / "index.html"
    render_html(SAMPLE_ARTICLES, output_path=out)
    content = out.read_text()
    assert "Summary of newer article." in content


def test_render_html_articles_newest_first(tmp_path):
    out = tmp_path / "index.html"
    render_html(SAMPLE_ARTICLES, output_path=out)
    content = out.read_text()
    assert content.index("Newer Article") < content.index("Older Article")


def test_render_html_uses_placeholder_when_no_thumbnail(tmp_path):
    out = tmp_path / "index.html"
    render_html(SAMPLE_ARTICLES, output_path=out)
    content = out.read_text()
    assert "no-thumbnail" in content


def test_render_html_links_to_articles(tmp_path):
    out = tmp_path / "index.html"
    render_html(SAMPLE_ARTICLES, output_path=out)
    content = out.read_text()
    assert "https://pbsanews.co.uk/article-1" in content


def test_render_rss_is_valid_xml(tmp_path):
    out = tmp_path / "feed.xml"
    render_rss(SAMPLE_ARTICLES, output_path=out)
    tree = ET.parse(out)
    root = tree.getroot()
    assert root.tag == "rss"
    assert root.attrib.get("version") == "2.0"


def test_render_rss_contains_items(tmp_path):
    out = tmp_path / "feed.xml"
    render_rss(SAMPLE_ARTICLES, output_path=out)
    tree = ET.parse(out)
    items = tree.findall(".//item")
    assert len(items) == 2


def test_render_rss_item_has_title_link_description(tmp_path):
    out = tmp_path / "feed.xml"
    render_rss(SAMPLE_ARTICLES, output_path=out)
    tree = ET.parse(out)
    first_item = tree.find(".//item")
    assert first_item.find("title").text == "Newer Article"
    assert "pbsanews.co.uk/article-2" in first_item.find("link").text
    assert first_item.find("description").text == "Summary of newer article."
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_renderer.py -v
```
Expected: `ModuleNotFoundError: No module named 'renderer'`

- [ ] **Step 3: Implement renderer.py**

```python
# renderer.py
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import date as date_type

PLACEHOLDER_COLOR = "#d1d5db"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PBSA News Digest</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #f4f6f8; margin: 0; padding: 0; color: #333; }}
  header {{ background: #1a3a5c; color: white; padding: 16px 24px; }}
  header h1 {{ margin: 0; font-size: 20px; }}
  header p {{ margin: 4px 0 0; font-size: 13px; opacity: 0.8; }}
  main {{ max-width: 860px; margin: 24px auto; padding: 0 16px; }}
  .card {{ display: flex; background: white; border-radius: 8px;
           border: 1px solid #e0e0e0; overflow: hidden; margin-bottom: 12px; }}
  .card-thumb {{ width: 160px; min-width: 160px; height: 110px; object-fit: cover; }}
  .card-thumb-placeholder {{ width: 160px; min-width: 160px; height: 110px;
                              background: {placeholder}; }}
  .card-body {{ padding: 12px 16px; display: flex; flex-direction: column;
                justify-content: space-between; flex: 1; }}
  .card-meta {{ font-size: 11px; color: #888; margin-bottom: 4px; }}
  .card-headline {{ font-weight: 700; color: #1a3a5c; font-size: 15px; margin-bottom: 6px; }}
  .card-summary {{ font-size: 13px; color: #555; line-height: 1.5; flex: 1; }}
  .card-link {{ font-size: 12px; color: #2563eb; text-decoration: none; margin-top: 8px; }}
  .card-link:hover {{ text-decoration: underline; }}
  footer {{ text-align: center; font-size: 11px; color: #aaa; padding: 24px; }}
</style>
</head>
<body>
<header>
  <h1>PBSA News Digest</h1>
  <p>Updated {updated}</p>
</header>
<main>
{cards}
</main>
<footer>PBSA News Digest &middot; Powered by Google Gemini</footer>
</body>
</html>"""

CARD_WITH_IMAGE = """<div class="card">
  <img class="card-thumb" src="{thumbnail_url}" alt="" loading="lazy"/>
  <div class="card-body">
    <div>
      <div class="card-meta">{source_name} &middot; {date}</div>
      <div class="card-headline">{headline}</div>
      <div class="card-summary">{summary}</div>
    </div>
    <a class="card-link" href="{url}" target="_blank" rel="noopener">Read full article</a>
  </div>
</div>"""

CARD_NO_IMAGE = """<div class="card">
  <div class="card-thumb-placeholder no-thumbnail"></div>
  <div class="card-body">
    <div>
      <div class="card-meta">{source_name} &middot; {date}</div>
      <div class="card-headline">{headline}</div>
      <div class="card-summary">{summary}</div>
    </div>
    <a class="card-link" href="{url}" target="_blank" rel="noopener">Read full article</a>
  </div>
</div>"""


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def render_html(articles: list[dict], output_path: Path = Path("output/index.html")) -> None:
    sorted_articles = sorted(articles, key=lambda a: a.get("scraped_at", ""), reverse=True)
    cards = []
    for a in sorted_articles:
        tmpl = CARD_WITH_IMAGE if a.get("thumbnail_url") else CARD_NO_IMAGE
        cards.append(tmpl.format(
            thumbnail_url=_escape(a.get("thumbnail_url") or ""),
            source_name=_escape(a["source_name"]),
            date=_escape(a["date"]),
            headline=_escape(a["headline"]),
            summary=_escape(a.get("summary") or a["body_text"][:200]),
            url=_escape(a["url"]),
        ))
    html = HTML_TEMPLATE.format(
        placeholder=PLACEHOLDER_COLOR,
        updated=date_type.today().strftime("%-d %B %Y"),
        cards="\n".join(cards),
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html, encoding="utf-8")


def render_rss(articles: list[dict], output_path: Path = Path("output/feed.xml")) -> None:
    sorted_articles = sorted(articles, key=lambda a: a.get("scraped_at", ""), reverse=True)

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "PBSA News Digest"
    ET.SubElement(channel, "link").text = "https://YOUR_GITHUB_USERNAME.github.io/pbsa-news/"
    ET.SubElement(channel, "description").text = "Daily PBSA industry news with AI summaries"

    for a in sorted_articles:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = a["headline"]
        ET.SubElement(item, "link").text = a["url"]
        ET.SubElement(item, "description").text = a.get("summary") or a["body_text"][:200]
        ET.SubElement(item, "pubDate").text = a["date"]
        ET.SubElement(item, "guid").text = a["url"]

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(output_path), encoding="unicode", xml_declaration=True)
```

- [ ] **Step 4: Run all renderer tests**

```bash
pytest tests/test_renderer.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add renderer.py tests/test_renderer.py
git commit -m "feat: HTML and RSS renderer"
```

---

## Task 6: Email Notifier

**Files:**
- Create: `notifier.py`
- Create: `tests/test_notifier.py`

Sends an HTML digest via Brevo REST API. Always sends -- if no new articles, sends a "no new articles today" message.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_notifier.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_notifier.py -v
```
Expected: `ModuleNotFoundError: No module named 'notifier'`

- [ ] **Step 3: Implement notifier.py**

```python
# notifier.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_notifier.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add notifier.py tests/test_notifier.py
git commit -m "feat: Brevo email digest with no-articles fallback"
```

---

## Task 7: Main Orchestrator

**Files:**
- Create: `main.py`

Wires all modules into the daily pipeline. Reads secrets from environment variables.

- [ ] **Step 1: Implement main.py**

```python
# main.py
import os
import logging
from datetime import date

from sources import SOURCES, EMAIL_RECIPIENTS, EMAIL_SENDER_ADDRESS, EMAIL_SENDER_NAME, EMAIL_SUBJECT
from store import load_store, save_store, add_articles
from scraper import fetch_source, enrich_article
from summariser import summarise_article
from renderer import render_html, render_rss
from notifier import send_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run():
    gemini_key = os.environ["GEMINI_API_KEY"]
    brevo_key = os.environ["BREVO_API_KEY"]
    today = date.today().isoformat()

    logging.info("Loading article store")
    existing = load_store()

    all_scraped = []
    for source in SOURCES:
        logging.info("Scraping %s", source["name"])
        try:
            articles = fetch_source(source)
            articles = [enrich_article(a) for a in articles]
            all_scraped.extend(articles)
        except Exception as e:
            logging.warning("Failed to scrape %s: %s", source["name"], e)

    merged, new_articles = add_articles(existing, all_scraped, return_new=True)
    logging.info("Found %d new articles", len(new_articles))

    for article in new_articles:
        logging.info("Summarising: %s", article["headline"])
        summarise_article(article, api_key=gemini_key)

    save_store(merged)
    logging.info("Store saved (%d total articles)", len(merged))

    render_html(merged)
    render_rss(merged)
    logging.info("Output files written")

    email_config = {
        "api_key": brevo_key,
        "sender_address": EMAIL_SENDER_ADDRESS,
        "sender_name": EMAIL_SENDER_NAME,
        "recipients": EMAIL_RECIPIENTS,
        "subject": EMAIL_SUBJECT,
    }
    send_digest(new_articles, config=email_config, today=today)
    logging.info("Email digest sent")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
python -c "import main; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all 21 tests PASS

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: main pipeline orchestrator"
```

---

## Task 8: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/daily.yml`
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```
output/
__pycache__/
*.pyc
.env
.superpowers/
```

Remove the output placeholder:

```bash
git rm --cached output/.gitkeep
```

- [ ] **Step 2: Create workflow file**

```bash
mkdir -p .github/workflows
```

`.github/workflows/daily.yml`:

```yaml
name: Daily PBSA News Digest

on:
  schedule:
    - cron: "0 7 * * *"   # 7am UTC daily
  workflow_dispatch:        # allow manual trigger from GitHub UI

permissions:
  contents: write

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run pipeline
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          BREVO_API_KEY: ${{ secrets.BREVO_API_KEY }}
        run: python main.py

      - name: Commit updated article store
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/articles.json
          git diff --cached --quiet || git commit -m "chore: update article store [skip ci]"
          git push

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./output
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore .github/workflows/daily.yml
git commit -m "feat: GitHub Actions daily workflow and GitHub Pages deployment"
```

---

## Task 9: GitHub Setup and SharePoint Embed

Manual steps -- no code required.

- [ ] **Step 1: Create GitHub repo and push**

```bash
git remote add origin https://github.com/YOUR_USERNAME/pbsa-news.git
git push -u origin main
```

- [ ] **Step 2: Add GitHub Secrets**

Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:
- `GEMINI_API_KEY` -- from Google AI Studio at aistudio.google.com (free, no card needed)
- `BREVO_API_KEY` -- from Brevo dashboard -> SMTP & API -> API Keys

- [ ] **Step 3: Enable GitHub Pages**

Repo Settings -> Pages -> Source: Deploy from a branch -> Branch: gh-pages / root -> Save.

- [ ] **Step 4: Update the RSS feed link in renderer.py**

Replace `YOUR_GITHUB_USERNAME` in `render_rss()`:

```python
ET.SubElement(channel, "link").text = "https://YOURUSERNAME.github.io/pbsa-news/"
```

Commit and push.

- [ ] **Step 5: Trigger a manual run**

Repo -> Actions -> Daily PBSA News Digest -> Run workflow. Verify:
- `data/articles.json` updated on main branch
- `gh-pages` branch contains `index.html` and `feed.xml`
- GitHub Pages URL loads correctly in browser

- [ ] **Step 6: Embed in SharePoint Online**

1. Open SharePoint site -> edit a page
2. Click + -> search "Embed"
3. Paste GitHub Pages URL: `https://YOURUSERNAME.github.io/pbsa-news/`
4. Publish the page

If Embed web part is blocked by tenant policy, use Quick Links web part with a direct link instead.

- [ ] **Step 7: Add remaining sources to sources.py**

For each PBSA news source, find its RSS feed URL (usually at `/feed/` or `/rss/`) and add an entry:

```python
{
    "name": "Inside Housing",
    "domain": "insidehousing.co.uk",
    "feed_url": "https://www.insidehousing.co.uk/rss",
},
```

Commit and push. The next run will pick up new sources automatically.
