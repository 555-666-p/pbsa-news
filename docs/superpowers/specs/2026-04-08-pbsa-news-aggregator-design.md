# PBSA News Aggregator — Design

**Date:** 2026-04-08  
**Status:** Approved

## Overview

A daily-refreshing news aggregator for PBSA (Purpose Built Student Accommodation) industry news. A Python script runs on a schedule, scrapes configured public news sources, generates AI summaries via Google Gemini, produces a static HTML page and RSS feed, and sends a daily email digest via Brevo. The page is published to GitHub Pages and embedded in a SharePoint Online page for colleague access.

## Architecture

```
GitHub Actions (daily cron, 7am)
  → scraper.py      — fetches articles, appends new ones to data/articles.json (deduped by URL)
  → summariser.py   — calls Gemini API for 1–2 sentence summaries on new articles only
  → renderer.py     — generates index.html and feed.xml from full archive
  → notifier.py     — sends daily digest email via Brevo API (today's new articles only)
  → GitHub Pages    — hosts index.html and feed.xml
  → SharePoint Online Embed web part — colleagues access via iframe
```

Everything lives in a single GitHub repository. No server, no database, no infrastructure to manage.

## Components

### `sources.py`
A plain config list of PBSA news source URLs. Adding or removing sources requires only editing this file.

### `scraper.py`
Fetches each source URL and uses BeautifulSoup to extract, per article:
- Headline
- Link (absolute URL)
- Publication date
- Article body text (for summarisation)
- Thumbnail image URL (from `og:image` meta tag)

Appends newly discovered articles to `data/articles.json`, deduplicated by URL. Articles already in the store are skipped.

### `summariser.py`
Sends article body text to the Google Gemini Flash API and returns a 1–2 sentence plain-English summary. Only runs on articles that don't already have a summary (i.e. new ones from the current run). Uses Gemini's free tier (up to 1,500 requests/day — well within daily usage).

### `renderer.py`
Reads the full `data/articles.json` archive and writes two output files:
- `index.html` — card feed UI showing all articles, newest-first
- `feed.xml` — standard RSS 2.0 feed of all articles

### `notifier.py`
Reads only the articles added in the current run and sends a daily digest email via the Brevo API. The email is an HTML digest: same card layout as the web page but formatted for email. Brevo credentials are stored as GitHub Actions secrets.

### GitHub Actions workflow
Runs daily at 7am. Executes the modules in sequence, commits updated `data/articles.json` and generated output files to the repo, pushes to `gh-pages` branch for GitHub Pages deployment, then triggers the email send.

## UI Design

Card feed layout. Each card contains:

| Element | Detail |
|---|---|
| Thumbnail | Scraped from article `og:image`, displayed at fixed 160×110px with `object-fit: cover` |
| Source | Publication name and domain, small grey text |
| Date | Relative (Today / Yesterday) or formatted date |
| Headline | Bold, linked to original article, opens in new tab |
| AI summary | 1–2 sentences, Gemini-generated |

Cards are stacked vertically, full width, with a light background. Clean, minimal styling — readable at a glance.

The page shows all articles ever scraped, newest-first — an accumulating archive. Each daily run appends newly discovered articles (deduplicated by URL) to the archive.

## RSS Feed

`feed.xml` is a standard RSS 2.0 file generated alongside `index.html` on every run. It contains all archived articles with headline, link, publication date, and AI summary as the item description. Colleagues can subscribe in any RSS reader; Outlook supports RSS natively via the email sidebar.

## Email Digest

A daily HTML email sent via Brevo to a configured recipient list. Contains only that day's new articles — not the full archive. Uses the same card structure as the web UI (thumbnail, source, headline, summary, read link).

- **Provider:** Brevo (free tier: 300 emails/day — sufficient)
- **Auth:** Brevo API key stored as a GitHub Actions secret (`BREVO_API_KEY`)
- **Recipients:** Defined in `sources.py` config alongside the news sources
- **Send time:** Immediately after the daily scrape completes (~7am)
- **No new articles:** Email is still sent with a "no new articles today" message

## SharePoint Integration

The GitHub Pages URL is embedded in a SharePoint Online modern page using the built-in **Embed** web part (no custom code or admin rights required). If the tenant blocks external iframes, fallback is a direct link on the SharePoint page.

## AI Summarisation

- **Model:** Google Gemini Flash (free tier)
- **Prompt:** Article body text → 1–2 sentence summary focused on the key news point
- **Free tier limit:** ~1,500 requests/day — sufficient for any realistic number of PBSA sources
- **Fallback:** If summarisation fails for an article, the first ~200 characters of body text are used instead

## Error Handling

| Scenario | Behaviour |
|---|---|
| News source unreachable | That source is skipped; rest of run completes normally |
| Article has no `og:image` | Neutral grey placeholder fills the thumbnail slot |
| Gemini API failure on an article | First ~200 chars of article body used as fallback summary |
| Gemini API fully down | Run completes with all fallback summaries; logged as warning |
| Brevo API failure | Email send is skipped; logged as warning; web and RSS output unaffected |
| No new articles found | RSS and web updated normally; email sent with "no new articles today" message |

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python | Practical, readable, good library support |
| Scraping | requests + BeautifulSoup | Simple, reliable for public HTML pages |
| AI | Google Gemini Flash API | Free tier, capable, easy SDK |
| Email | Brevo API | Free tier (300/day), clean HTML email output |
| Scheduling | GitHub Actions cron | Free, reliable, no infrastructure |
| Hosting | GitHub Pages | Free static hosting, auto-deploys from repo |
| UI access | SharePoint Online Embed web part | No dev work required, native M365 |

## Out of Scope (v1)

- Search or filtering
- Per-user personalisation
- Mobile-specific layout optimisation
