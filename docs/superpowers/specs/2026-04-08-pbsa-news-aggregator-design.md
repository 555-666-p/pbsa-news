# PBSA News Aggregator — Design

**Date:** 2026-04-08  
**Status:** Approved

## Overview

A daily-refreshing news aggregator for PBSA (Purpose Built Student Accommodation) industry news. A Python script runs on a schedule, scrapes configured public news sources, generates AI summaries via Google Gemini, and produces a static HTML page. The page is published to GitHub Pages and embedded in a SharePoint Online page for colleague access.

## Architecture

```
GitHub Actions (daily cron, 7am)
  → scraper.py — fetches articles from configured sources
  → summariser.py — calls Gemini API for 1–2 sentence summaries
  → renderer.py — generates static index.html
  → GitHub Pages — hosts the output
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

### `summariser.py`
Sends article body text to the Google Gemini Flash API and returns a 1–2 sentence plain-English summary. Uses Gemini's free tier (up to 1,500 requests/day — well within daily usage).

### `renderer.py`
Takes the list of scraped and summarised articles and writes `index.html`. Produces a card feed layout: one card per article, each showing a fixed-size thumbnail, source name, date, headline (linked), and AI summary.

### GitHub Actions workflow
Runs daily at 7am. Calls the modules in sequence, then commits and pushes the generated `index.html` to the `gh-pages` branch, triggering a GitHub Pages deployment.

## UI Design

Card feed layout. Each card contains:

| Element | Detail |
|---|---|
| Thumbnail | Scraped from article `og:image`, displayed at fixed 160×110px with `object-fit: cover` |
| Source | Publication name and domain, small grey text |
| Date | Relative (Today / Yesterday) or formatted date |
| Headline | Bold, linked to original article, opens in new tab |
| AI summary | 1–2 sentences, Gemini-generated |

Cards are stacked vertically, full width, with a light background. Clean, minimal styling — readable at a glance.\n\nThe page shows the current day\'s scrape only — a fresh snapshot each run, not an accumulating archive. Articles are ordered newest-first within each run.

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

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python | Practical, readable, good library support |
| Scraping | requests + BeautifulSoup | Simple, reliable for public HTML pages |
| AI | Google Gemini Flash API | Free tier, capable, easy SDK |
| Scheduling | GitHub Actions cron | Free, reliable, no infrastructure |
| Hosting | GitHub Pages | Free static hosting, auto-deploys from repo |
| UI access | SharePoint Online Embed web part | No dev work required, native M365 |

## Out of Scope (v1)

- Search or filtering
- Email digest / notifications
- Per-user personalisation
- RSS feed output
- Mobile-specific layout optimisation
