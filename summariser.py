from openai import OpenAI

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
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        prompt = PROMPT_TEMPLATE.format(
            headline=article["headline"],
            body=article["body_text"][:2000],
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
        )
        article["summary"] = response.choices[0].message.content.strip()
    except Exception:
        article["summary"] = article["body_text"][:200]
    return article
