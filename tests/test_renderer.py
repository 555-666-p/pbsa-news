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
