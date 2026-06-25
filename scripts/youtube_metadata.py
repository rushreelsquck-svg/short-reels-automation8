"""
youtube_metadata.py
Merges the story-specific tags/hashtags from generate_script.py with real
trending keywords pulled from the YouTube "mostPopular" chart, then trims
everything to YouTube's actual limits so the upload never gets rejected:
  - tags field: 500 characters total (combined), each tag <= ~30 chars by convention
  - title: 100 characters
  - description: 5000 characters
"""

MAX_TAGS_CHARS = 480  # leave a little headroom under YouTube's 500-char cap
MAX_TITLE_CHARS = 95
MAX_DESCRIPTION_CHARS = 4800


def _dedupe_preserve_order(items):
    seen = set()
    out = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def build_final_metadata(script_package: dict, trending_keywords: list[str], topic: dict) -> dict:
    title = script_package.get("title", topic.get("title", "Trending Today"))[:MAX_TITLE_CHARS]

    hashtags = _dedupe_preserve_order(script_package.get("hashtags", ["#shorts"]))
    hashtag_line = " ".join(hashtags)

    description_text = script_package.get("description", "").strip() or script_package.get("script", "").strip()

    description_parts = [
        description_text,
        "",
        f"Source story: {topic.get('source', '')}".strip(),
        "",
        hashtag_line,
    ]
    description = "\n".join(p for p in description_parts if p)[:MAX_DESCRIPTION_CHARS]

    # tags = the story-specific tags first (most relevant), then trending keywords as filler
    combined_tags = _dedupe_preserve_order(script_package.get("tags", []) + trending_keywords + ["shorts", "entertainment", "celebrity", "popculture"])

    final_tags = []
    char_budget = MAX_TAGS_CHARS
    for tag in combined_tags:
        if len(tag) + 1 > char_budget:
            break
        final_tags.append(tag)
        char_budget -= len(tag) + 1  # +1 for the implicit comma YouTube uses internally

    return {
        "title": title,
        "description": description,
        "tags": final_tags,
    }
