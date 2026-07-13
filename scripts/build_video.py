"""
build_video.py — news-style channels (Pulse Brief, The Uptick, The Buzzer, The Marquee)

Assembles the final 1080x1920 vertical Short:
  - background: cuts between real Pexels stock clips, one per visual query.
    Clip selection is smarter than random: prefers portrait files, picks the
    highest-resolution portrait clip available, and falls back to a shorter
    2-word version of the query if the original returns no results — so a very
    specific query like "oil tanker unloading at night port" that Pexels doesn't
    have still gets a reasonable clip rather than a gradient.
  - captions: phrase-by-phrase (5 words at a time), 58px Anton font, positioned
    at 74% down — cleaner and more like modern Shorts style than the old 72px
    text sitting at 62%.
  - audio: voiceover, optionally mixed with royalty-free music from assets/music/.

Fixes applied vs previous version:
  - Stretched clip: resize condition was inverted. resize(height=H) and
    resize(width=W) were swapped, so portrait clips were resized the wrong
    direction and then force-stretched to fill. Now correct.
  - Caption font 72px → 58px, wrap 16 chars → 22, position 62% → 74%.
  - Clip selection: random → highest-res portrait; with query fallback.
"""
import math
import os
import random
import textwrap
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS  # Pillow >=10 compat shim for moviepy 1.0.3

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
    afx,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
FONT_PATH = ASSETS_DIR / "fonts" / "Anton-Regular.ttf"
MUSIC_DIR = ASSETS_DIR / "music"

W, H = 1080, 1920
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")


def _split_into_phrases(script_text, words_per_phrase=5):
    words = script_text.split()
    return [" ".join(words[i:i + words_per_phrase]) for i in range(0, len(words), words_per_phrase)] or [""]


def _render_caption_png(text, font_size=58, max_width=960):
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    wrapped = textwrap.fill(text, width=22)
    lines = wrapped.split("\n")

    dummy = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(dummy)
    line_h = max(d.textbbox((0, 0), line, font=font)[3] for line in lines) + 16
    img_h = line_h * len(lines) + 36

    img = Image.new("RGBA", (max_width, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, max_width, img_h], radius=20, fill=(0, 0, 0, 150))

    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (max_width - line_w) / 2
        y = 18 + idx * line_h
        draw.text((x, y), line, font=font, fill="white", stroke_width=4, stroke_fill="black")

    return np.array(img)


def _best_portrait_file(video_files):
    """Pick the highest-resolution portrait (h > w) video file available."""
    portrait = [f for f in video_files if f.get("height", 0) > f.get("width", 0)]
    candidates = portrait if portrait else video_files
    return max(candidates, key=lambda f: f.get("width", 0) * f.get("height", 0))


def _search_pexels(query, per_page=10):
    """Search Pexels for portrait clips; returns list of video dicts or []."""
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "orientation": "portrait", "per_page": per_page},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("videos", [])
    except Exception:
        return []


def _download_and_prepare_clip(video, duration):
    """Download a Pexels video dict and return a cropped, darkened VideoFileClip."""
    pick = _best_portrait_file(video["video_files"])
    local_path = f"/tmp/pexels_bg_{abs(hash(pick['link']))}.mp4"
    with requests.get(pick["link"], stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    clip = VideoFileClip(local_path)
    # Correct resize: portrait clips (h/w > H/W) need resize(width=W) so height
    # exceeds H and can be cropped; landscape-ish clips need resize(height=H).
    clip = clip.resize(width=W) if (clip.h / clip.w) > (H / W) else clip.resize(height=H)
    clip = clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=W, height=H)

    if clip.duration < duration:
        clip = concatenate_videoclips([clip] * math.ceil(duration / clip.duration))
    clip = clip.subclip(0, duration)
    clip = clip.fl_image(lambda frame: (frame * 0.55).astype("uint8"))
    return clip


def _fetch_pexels_clip(query, duration):
    """
    Try the exact query first; if no results, fall back to the first two words
    (a broader, simpler search that almost always returns something). Returns
    a prepared clip or None if everything fails.
    """
    if not PEXELS_API_KEY:
        return None
    try:
        results = _search_pexels(query, per_page=10)

        if not results:
            short_query = " ".join(query.split()[:2])
            if short_query and short_query != query:
                results = _search_pexels(short_query, per_page=10)

        if not results:
            return None

        video = random.choice(results)
        return _download_and_prepare_clip(video, duration)

    except Exception:
        return None


def _build_background_sequence(visual_queries, total_duration):
    visual_queries = [q for q in (visual_queries or []) if q.strip()]

    if not PEXELS_API_KEY or not visual_queries:
        return _make_gradient_background(total_duration)

    n = len(visual_queries)
    seg_duration = total_duration / n
    segments = []
    accounted = 0.0
    for i, query in enumerate(visual_queries):
        this_duration = (total_duration - accounted) if i == n - 1 else seg_duration
        clip = _fetch_pexels_clip(query, this_duration)
        if clip is None:
            clip = _make_gradient_background(this_duration)
        segments.append(clip.resize((W, H)))
        accounted += this_duration

    return concatenate_videoclips(segments)


def _make_gradient_background(duration, color_a=(20, 20, 45), color_b=(95, 20, 110)):
    yy, xx = np.mgrid[0:H, 0:W]
    diag = (xx + yy) / (W + H)

    def make_frame(t):
        progress = (math.sin(t * 0.4) + 1) / 2
        mix = np.array(color_a) * (1 - progress) + np.array(color_b) * progress
        shift = 0.15 * math.sin(t * 0.6)
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        for c in range(3):
            variation = 40 * np.sin(2 * math.pi * (diag + shift))
            frame[:, :, c] = np.clip(mix[c] + variation, 0, 255)
        return frame

    return VideoClip(make_frame, duration=duration)


def build_video(script_text, audio_path, output_path, visual_queries=None):
    voice = AudioFileClip(audio_path)
    duration = voice.duration + 2.0

    background = _build_background_sequence(visual_queries, duration)
    background = background.set_duration(duration).resize((W, H))

    phrases = _split_into_phrases(script_text)
    total_words = sum(len(p.split()) for p in phrases) or 1
    caption_clips = []
    t = 0.0
    for phrase in phrases:
        seg_duration = max(0.6, voice.duration * (len(phrase.split()) / total_words))
        png = _render_caption_png(phrase)
        clip = (
            ImageClip(png)
            .set_start(t)
            .set_duration(seg_duration)
            .set_position(("center", int(H * 0.74)))
        )
        caption_clips.append(clip)
        t += seg_duration

    outro_png = _render_caption_png("Follow for more celebrity news every single day.")
    caption_clips.append(
        ImageClip(outro_png)
        .set_start(voice.duration + 0.2)
        .set_duration(1.8)
        .set_position(("center", int(H * 0.74)))
    )

    audio_tracks = [voice.set_start(0)]
    music_files = list(MUSIC_DIR.glob("*.mp3"))
    if music_files:
        music = AudioFileClip(str(random.choice(music_files))).fx(afx.audio_loop, duration=duration)
        music = music.fx(afx.volumex, 0.18)
        audio_tracks.append(music)

    final_audio = CompositeAudioClip(audio_tracks).set_duration(duration)
    final_video = CompositeVideoClip([background, *caption_clips], size=(W, H)).set_duration(duration)
    final_video = final_video.set_audio(final_audio)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final_video.write_videofile(
        output_path, fps=30, codec="libx264", audio_codec="aac",
        threads=4, preset="medium", logger=None,
    )
    return output_path
