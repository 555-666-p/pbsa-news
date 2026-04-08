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
<footer>PBSA News Digest &middot; Powered by DeepSeek</footer>
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


def render_html(articles: list, output_path: Path = Path("output/index.html")) -> None:
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


def render_rss(articles: list, output_path: Path = Path("output/feed.xml")) -> None:
    sorted_articles = sorted(articles, key=lambda a: a.get("scraped_at", ""), reverse=True)

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "PBSA News Digest"
    ET.SubElement(channel, "link").text = "https://555-666-p.github.io/pbsa-news/"
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
