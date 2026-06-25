"""
generate_audio.py
High-quality voiceover via OpenAI's TTS API — a full day's script costs a
fraction of a cent (tts-1 is $15 per 1M characters; one ~800-character
script is roughly $0.012). Falls back automatically to the old free gTTS
voice if OPENAI_API_KEY isn't set, or if the API call fails for any reason
— a transient outage degrades the voice quality for one run, it doesn't
break the pipeline.

Voices (tts-1 / tts-1-hd): alloy, ash, coral, echo, fable, nova, onyx, sage,
shimmer. gpt-4o-mini-tts adds: ballad, verse, marin, cedar. Sample a few at
platform.openai.com/playground/tts to pick one that fits the channel's tone
— set it per-channel via OPENAI_TTS_VOICE in that repo's workflow file.
"""
import os
from pathlib import Path

import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "tts-1")
OPENAI_TTS_VOICE = os.environ.get("OPENAI_TTS_VOICE", "onyx")


def _generate_with_openai(text, output_path):
    resp = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={"model": OPENAI_TTS_MODEL, "voice": OPENAI_TTS_VOICE, "input": text},
        timeout=60,
    )
    resp.raise_for_status()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)
    return output_path


def _generate_with_gtts(text, output_path):
    from gtts import gTTS
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    gTTS(text=text, lang="en", slow=False).save(output_path)
    return output_path


def generate_voiceover(text: str, output_path: str) -> str:
    if OPENAI_API_KEY:
        try:
            return _generate_with_openai(text, output_path)
        except Exception as e:
            print(f"OpenAI TTS failed ({e}), falling back to gTTS for this run")
    return _generate_with_gtts(text, output_path)


if __name__ == "__main__":
    generate_voiceover("This is a test of the voiceover system.", "/tmp/test_audio.mp3")
    print("Saved /tmp/test_audio.mp3")
