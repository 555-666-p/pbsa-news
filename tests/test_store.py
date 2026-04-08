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
