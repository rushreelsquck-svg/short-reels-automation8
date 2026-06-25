"""
fetch_trend.py
Pulls today's top trending headlines from Google News RSS (no API key required)
and skips anything we've already made a video about (tracked in state/used_topics*.json).

Why Google News RSS instead of scraping a "trending" site:
- It's a stable, public, free feed (no key, no rate-limit headaches).
- It gives us real news content to base an ORIGINAL script on, instead of
  re-uploading anyone else's video or article text.

STATE_SUFFIX env var lets multiple channels share this same codebase without
sharing "already used" history — e.g. STATE_SUFFIX=_channel2 tracks state in
state/used_topics_channel2.json instead of state/used_topics.json.

Two ways to narrow the feed to a niche instead of general top stories:
- NEWS_TOPIC_SECTION: one of Google News' own curated section feeds —
  WORLD, NATION, BUSINESS, TECHNOLOGY, ENTERTAINMENT, SPORTS, SCIENCE, HEALTH.
  Best for broad coverage of an entire category (e.g. all sports/leagues).
- NEWS_TOPIC_QUERY: a free-text search query for something more specific
  than a whole section (e.g. "personal finance OR investing OR side hustle").
If both are set, NEWS_TOPIC_SECTION takes priority. Leave both unset for
general top headlines.
"""
import json
import os
import re
import urllib.parse
from pathlib import Path

import feedparser

STATE_SUFFIX = os.environ.get("STATE_SUFFIX", "")
STATE_FILE = Path(__file__).resolve().parent.parent / "state" / f"used_topics{STATE_SUFFIX}.json"


def _load_used_topics():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def _save_used_topic(title):
    used = _load_used_topics()
    used.add(title)
    # keep only the last 200 so the file doesn't grow forever
    trimmed = list(used)[-200:]
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(trimmed, indent=2))


def _clean_title(raw_title):
    # Google News titles look like "Headline text - Source Name". Strip the source.
    return re.sub(r"\s+-\s+[^-]+$", "", raw_title).strip()


def get_trending_topic(region="US", language="en", topic_query=None, topic_section=None):
    """Returns a dict: {title, summary, link, source} for the top unused trending story."""
    if topic_section:
        url = f"https://news.google.com/rss/headlines/section/topic/{topic_section.upper()}?hl={language}-{region}&gl={region}&ceid={region}:{language}"
    elif topic_query:
        q = urllib.parse.quote(topic_query)
        url = f"https://news.google.com/rss/search?q={q}&hl={language}-{region}&gl={region}&ceid={region}:{language}"
    else:
        url = f"https://news.google.com/rss?hl={language}-{region}&gl={region}&ceid={region}:{language}"
    feed = feedparser.parse(url)

    if not feed.entries:
        raise RuntimeError("Google News RSS returned no entries — check region/language codes or topic settings.")

    used = _load_used_topics()

    for entry in feed.entries:
        title = _clean_title(entry.title)
        if title in used:
            continue

        summary = re.sub(r"<[^>]+>", "", getattr(entry, "summary", "")).strip()

        topic = {
            "title": title,
            "summary": summary,
            "link": entry.link,
            "source": getattr(entry, "source", {}).get("title", "") if hasattr(entry, "source") else "",
        }
        _save_used_topic(title)
        return topic

    raise RuntimeError("All current top headlines were already used today. Try again later or widen the feed.")


if __name__ == "__main__":
    topic = get_trending_topic(
        region=os.environ.get("NEWS_REGION", "US"),
        language=os.environ.get("NEWS_LANGUAGE", "en"),
        topic_query=os.environ.get("NEWS_TOPIC_QUERY"),
        topic_section=os.environ.get("NEWS_TOPIC_SECTION"),
    )
    print(json.dumps(topic, indent=2))
