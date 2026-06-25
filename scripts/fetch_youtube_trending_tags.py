"""
fetch_youtube_trending_tags.py
Reads the official YouTube "mostPopular" chart (public data, just needs an API key,
no OAuth) and harvests the tags/keywords those videos are actually using.

This is the closest free, official approximation of "most searched on YouTube" —
true search-volume rankings require a paid keyword tool (e.g. VidIQ/TubeBuddy),
which this script does not attempt to fake.
"""
import os
from collections import Counter

import requests

YOUTUBE_API_KEY = os.environ.get("YT_API_KEY", "")  # separate from the OAuth creds; a simple API key works for read-only public data


def get_trending_keywords(region="US", max_videos=20, top_n=15):
    if not YOUTUBE_API_KEY:
        return []  # caller should fall back to generic tags if this is empty

    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "snippet",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": max_videos,
            "key": YOUTUBE_API_KEY,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    counter = Counter()
    for item in data.get("items", []):
        for tag in item.get("snippet", {}).get("tags", []) or []:
            counter[tag.lower()] += 1

    return [tag for tag, _ in counter.most_common(top_n)]


if __name__ == "__main__":
    print(get_trending_keywords(region=os.environ.get("NEWS_REGION", "US")))
