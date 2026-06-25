"""
build_video.py
Assembles the final 1080x1920 vertical video:
  - background: cuts between a few real Pexels stock clips (free, royalty-free,
    no attribution required) — one per "visual query" Claude picked for this
    story — if PEXELS_API_KEY is set, otherwise a fully synthetic animated
    gradient (zero licensing risk, always works offline). Any single clip that
    can't be found falls back to a gradient for just that segment, so one bad
    lookup never breaks the whole video.
  - captions: phrase-by-phrase, rendered with Pillow using an open-source
    (OFL-licensed) font, timed proportionally across the voiceover
  - audio: the generated voiceover, optionally mixed with a royalty-free
    music bed from assets/music/ (you provide the mp3s — see README)
"""
import math
import os
import random
import textwrap
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

# moviepy 1.0.3's PIL-based resizer (used when OpenCV isn't installed) still
# references the old Image.ANTIALIAS constant, which Pillow >=10 removed.
# This restores it as an alias so .resize() doesn't crash.
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

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


def _split_into_phrases(script_text, words_per_phrase=4):
    words = script_text.split()
    return [" ".join(words[i:i + words_per_phrase]) for i in range(0, len(words), words_per_phrase)] or [""]


def _render_caption_png(text, font_size=72, max_width=950):
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    wrapped = textwrap.fill(text, width=16)
    lines = wrapped.split("\n")

    dummy = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(dummy)
    line_h = max(d.textbbox((0, 0), line, font=font)[3] for line in lines) + 22
    img_h = line_h * len(lines) + 50

    img = Image.new("RGBA", (max_width, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, max_width, img_h], radius=28, fill=(0, 0, 0, 140))

    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (max_width - line_w) / 2
        y = 25 + idx * line_h
        draw.text((x, y), line, font=font, fill="white", stroke_width=6, stroke_fill="black")

    return np.array(img)


def _fetch_pexels_clip(query, duration):
    if not PEXELS_API_KEY:
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "orientation": "portrait", "per_page": 5},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("videos", [])
        if not results:
            return None
        video = random.choice(results)
        files = sorted(video["video_files"], key=lambda f: f.get("width", 0))
        portrait = [f for f in files if f.get("height", 0) > f.get("width", 0)]
        pick = (portrait or files)[-1]

        local_path = f"/tmp/pexels_bg_{abs(hash(query))}.mp4"
        with requests.get(pick["link"], stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        clip = VideoFileClip(local_path)
        clip = clip.resize(height=H) if (clip.h / clip.w) > (H / W) else clip.resize(width=W)
        clip = clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=W, height=H)

        if clip.duration < duration:
            clip = concatenate_videoclips([clip] * math.ceil(duration / clip.duration))
        clip = clip.subclip(0, duration)
        clip = clip.fl_image(lambda frame: (frame * 0.55).astype("uint8"))  # darken for caption legibility
        return clip
    except Exception:
        return None  # any failure here just falls back to the gradient for this segment — never crashes the run


def _build_background_sequence(visual_queries, total_duration):
    """
    Cuts between a few relevant clips (one per visual query) instead of looping
    a single clip for the whole video. Falls back to the synthetic gradient —
    for the whole video if there's no Pexels key at all, or per-segment if a
    specific clip can't be found — so a single failed lookup never breaks the run.
    """
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
    """Fully synthetic animated diagonal gradient. No external assets, no licensing risk."""
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
    duration = voice.duration + 2.0  # +2s for the outro card

    background = _build_background_sequence(visual_queries, duration)
    background = background.set_duration(duration).resize((W, H))

    phrases = _split_into_phrases(script_text)
    total_words = sum(len(p.split()) for p in phrases) or 1
    caption_clips = []
    t = 0.0
    for phrase in phrases:
        seg_duration = max(0.6, voice.duration * (len(phrase.split()) / total_words))
        png = _render_caption_png(phrase)
        clip = ImageClip(png).set_start(t).set_duration(seg_duration).set_position(("center", int(H * 0.62)))
        caption_clips.append(clip)
        t += seg_duration

    outro_png = _render_caption_png("Follow for daily trending recaps")
    caption_clips.append(
        ImageClip(outro_png).set_start(voice.duration + 0.2).set_duration(1.8).set_position(("center", int(H * 0.62)))
    )

    audio_tracks = [voice.set_start(0)]
    music_files = list(MUSIC_DIR.glob("*.mp3"))
    if music_files:
        music = AudioFileClip(str(random.choice(music_files))).fx(afx.audio_loop, duration=duration)
        music = music.fx(afx.volumex, 0.12)
        audio_tracks.append(music)

    final_audio = CompositeAudioClip(audio_tracks).set_duration(duration)
    final_video = CompositeVideoClip([background, *caption_clips], size=(W, H)).set_duration(duration)
    final_video = final_video.set_audio(final_audio)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final_video.write_videofile(
        output_path, fps=30, codec="libx264", audio_codec="aac", threads=4, preset="medium", logger=None
    )
    return output_path


if __name__ == "__main__":
    from generate_audio import generate_voiceover

    demo_script = "Scientists just discovered something surprising about deep ocean coral. The reef survived a heatwave that killed nearby colonies. Researchers think a unique algae partnership made the difference. This could help protect other reefs as oceans keep warming."
    demo_queries = ["coral reef underwater", "ocean waves aerial", "marine biologist lab"]
    generate_voiceover(demo_script, "/tmp/demo_audio.mp3")
    build_video(demo_script, "/tmp/demo_audio.mp3", "/tmp/demo_output.mp4", visual_queries=demo_queries)
    print("Wrote /tmp/demo_output.mp4")
