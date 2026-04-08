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
    deepseek_key = os.environ["DEEPSEEK_API_KEY"]
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
        summarise_article(article, api_key=deepseek_key)

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
