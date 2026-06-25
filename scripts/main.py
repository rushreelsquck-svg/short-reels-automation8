"""
main.py
Runs the whole daily pipeline end to end. This is what the GitHub Actions
workflow calls. Each stage prints progress so failures are easy to spot in
the Actions log.
"""
import json
import os
import sys
import traceback
from pathlib import Path

from fetch_trend import get_trending_topic
from fetch_youtube_trending_tags import get_trending_keywords
from generate_script import generate_script_package
from generate_audio import generate_voiceover
from build_video import build_video
from youtube_metadata import build_final_metadata
from upload_video import upload_short

WORKDIR = Path("/tmp/trend_short_run")


def run():
    region = os.environ.get("NEWS_REGION", "US")
    language = os.environ.get("NEWS_LANGUAGE", "en")
    topic_query = os.environ.get("NEWS_TOPIC_QUERY")
    topic_section = os.environ.get("NEWS_TOPIC_SECTION")

    source_note = f', section="{topic_section}"' if topic_section else (f', query="{topic_query}"' if topic_query else "")
    print(f"[1/6] Fetching today's trending topic ({region}/{language}){source_note}...")
    topic = get_trending_topic(region=region, language=language, topic_query=topic_query, topic_section=topic_section)
    print(f"      -> {topic['title']}")

    print("[2/6] Fetching real YouTube trending keywords for hashtag enrichment...")
    trending_keywords = get_trending_keywords(region=region)
    print(f"      -> {len(trending_keywords)} keywords found")

    print("[3/6] Writing original script + title + description + tags (Claude)...")
    script_package = generate_script_package(topic, trending_keywords)
    print(f"      -> Title: {script_package['title']}")

    print("[4/6] Generating voiceover...")
    WORKDIR.mkdir(parents=True, exist_ok=True)
    audio_path = str(WORKDIR / "voice.mp3")
    generate_voiceover(script_package["script"], audio_path)

    print("[5/6] Building the video...")
    video_path = str(WORKDIR / "output.mp4")
    visual_queries = script_package.get("visual_queries", [])
    build_video(script_package["script"], audio_path, video_path, visual_queries=visual_queries)

    print("[6/6] Uploading to YouTube...")
    final_meta = build_final_metadata(script_package, trending_keywords, topic)
    video_id = upload_short(
        video_path=video_path,
        title=final_meta["title"],
        description=final_meta["description"],
        tags=final_meta["tags"],
    )

    print(json.dumps({"video_id": video_id, "title": final_meta["title"]}, indent=2))
    return video_id


if __name__ == "__main__":
    try:
        run()
    except Exception:
        print("PIPELINE FAILED:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
