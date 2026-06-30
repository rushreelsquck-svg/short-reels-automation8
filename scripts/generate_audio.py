"""
generate_audio.py
High-quality voiceover via OpenAI's TTS API — a full day's script costs a
fraction of a cent (tts-1 is $15 per 1M characters; one ~800-character
script is roughly $0.012). Falls back automatically to the old free gTTS
voice if OPENAI_API_KEY isn't set, or if the API call still fails after
retries — a transient outage degrades the voice quality for one run, it
doesn't break the pipeline.

Retries on HTTP 429 (rate limit) specifically, with exponential backoff —
channels that generate one TTS call per scene (multi-scene formats) can
fire off 6-9 calls back-to-back with no natural spacing, which is exactly
the pattern that exhausts a low free-tier rate limit. Spending $5 cumulative
on your OpenAI account auto-upgrades you to Tier 1 (500 RPM on most models),
which on its own usually eliminates this — the retry logic here is the
backstop for bursts even on a paid tier, not a substitute for that.

The gTTS fallback ALSO retries with backoff: GitHub Actions runners share
IP ranges with countless other automated scripts, and Google's translate
endpoint (which gTTS unofficially relies on) periodically blocks or
challenges those shared IPs with a "sorry/index" bot-check page — visible
in logs as a 429 pointing at google.com/sorry/index. That's an IP-reputation
issue, not a real rate limit on your usage, and it often clears within a
short wait.

Voices (tts-1 / tts-1-hd): alloy, ash, coral, echo, fable, nova, onyx, sage,
shimmer. gpt-4o-mini-tts adds: ballad, verse, marin, cedar. Sample a few at
platform.openai.com/playground/tts to pick one that fits the channel's tone
— set it per-channel via OPENAI_TTS_VOICE in that repo's workflow file.
"""
import os
import time
from pathlib import Path

import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "tts-1")
OPENAI_TTS_VOICE = os.environ.get("OPENAI_TTS_VOICE", "onyx")
MAX_RETRIES = 4
BASE_DELAY_SECONDS = 3  # 3s, 6s, 12s, 24s
GTTS_MAX_RETRIES = 3
GTTS_BASE_DELAY_SECONDS = 5  # 5s, 10s, 20s


def _generate_with_openai(text, output_path):
    last_error = None
    for attempt in range(MAX_RETRIES):
        resp = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": OPENAI_TTS_MODEL, "voice": OPENAI_TTS_VOICE, "input": text},
            timeout=60,
        )
        if resp.status_code == 429:
            last_error = requests.HTTPError(f"429 rate limited (attempt {attempt + 1}/{MAX_RETRIES})", response=resp)
            delay = BASE_DELAY_SECONDS * (2 ** attempt)
            print(f"OpenAI TTS rate-limited, retrying in {delay}s...")
            time.sleep(delay)
            continue
        resp.raise_for_status()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return output_path

    raise last_error


def _generate_with_gtts(text, output_path):
    from gtts import gTTS
    from gtts.tts import gTTSError

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for attempt in range(GTTS_MAX_RETRIES):
        try:
            gTTS(text=text, lang="en", slow=False).save(output_path)
            return output_path
        except gTTSError as e:
            last_error = e
            delay = GTTS_BASE_DELAY_SECONDS * (2 ** attempt)
            print(f"gTTS failed (likely a shared-IP bot-check from Google, not a real quota issue), retrying in {delay}s...")
            time.sleep(delay)

    raise last_error


def generate_voiceover(text: str, output_path: str) -> str:
    if OPENAI_API_KEY:
        try:
            return _generate_with_openai(text, output_path)
        except Exception as e:
            print(f"OpenAI TTS failed after retries ({e}), falling back to gTTS for this run")
    return _generate_with_gtts(text, output_path)


if __name__ == "__main__":
    generate_voiceover("This is a test of the voiceover system.", "/tmp/test_audio.mp3")
    print("Saved /tmp/test_audio.mp3")
