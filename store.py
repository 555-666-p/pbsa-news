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
