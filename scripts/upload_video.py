"""
upload_video.py
Uploads the finished MP4 to YouTube as a Short using a stored refresh token
(no browser/interactive login needed — this is what lets it run unattended
inside GitHub Actions).

YT_PRIVACY_STATUS supports an extra value beyond YouTube's own "public" /
"unlisted" / "private": set it to "scheduled" to upload as private with a
publishAt timestamp — YouTube then auto-flips it to public on its own at that
time, no manual step needed. How far in the future is controlled by
YT_PUBLISH_DELAY_HOURS (default 3).
"""
import datetime
import os
import re

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_authenticated_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


def _build_status_body():
    privacy_status = os.environ.get("YT_PRIVACY_STATUS", "unlisted")

    if privacy_status == "scheduled":
        delay_hours = float(os.environ.get("YT_PUBLISH_DELAY_HOURS", "3"))
        publish_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=delay_hours)
        return {
            "privacyStatus": "private",
            "publishAt": publish_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "selfDeclaredMadeForKids": False,
        }

    return {
        "privacyStatus": privacy_status,
        "selfDeclaredMadeForKids": False,
    }


def _sanitize_tags(tags: list[str]) -> list[str]:
    """
    YouTube rejects tags containing: < > & " ' #
    Strip those characters and drop any tag that ends up empty or over 100 chars.
    """
    cleaned = []
    for tag in tags:
        tag = re.sub(r'[<>&"\'\#]', '', tag).strip()
        if tag and len(tag) <= 100:
            cleaned.append(tag)
    return cleaned


def upload_short(video_path: str, title: str, description: str, tags: list[str]) -> str:
    youtube = _get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": _sanitize_tags(tags),
            "categoryId": os.environ.get("YT_CATEGORY_ID", "25"),
        },
        "status": _build_status_body(),
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"Uploaded: https://youtube.com/shorts/{video_id}")
    if "publishAt" in body["status"]:
        print(f"Scheduled to go public at: {body['status']['publishAt']}")
    return video_id


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python upload_video.py /path/to/video.mp4")
        sys.exit(1)
    upload_short(sys.argv[1], "Test upload", "Test description.", ["test"])
