"""
generate_music.py
Generates three royalty-free background music tracks using pure math (numpy + scipy)
and saves them as MP3 via ffmpeg. Run this once per repo to populate assets/music/.

Tracks:
  dark_documentary.mp3  — low drone, dissonant, tense. Vaults of History, Zero Warning.
  gentle_reverent.mp3   — warm pad, slow movement. Bible Time.
  upbeat_news.mp3       — punchy, modern, forward-motion. News channels (Pulse Brief, Uptick, Buzzer, Marquee).
  whimsical_warm.mp3    — gentle bells and warmth. Fable Story, Pantry Remedies.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SR = 44100
DURATION = 120  # 2 minutes — looped as needed in build_video.py


def _fade(audio, fade_sec=3.0):
    n = int(SR * fade_sec)
    audio = audio.copy().astype(np.float64)
    audio[:n] *= np.linspace(0, 1, n)
    audio[-n:] *= np.linspace(1, 0, n)
    return audio


def _normalize(audio, peak=0.55):
    m = np.max(np.abs(audio))
    return audio / m * peak if m > 0 else audio


def _to_mp3(audio_float, out_path):
    tmp = tempfile.mktemp(suffix=".wav")
    pcm = (_normalize(audio_float) * 32767).astype(np.int16)
    wavfile.write(tmp, SR, pcm)
    subprocess.run(
        ["ffmpeg", "-y", "-i", tmp, "-b:a", "128k", str(out_path)],
        check=True, capture_output=True,
    )
    Path(tmp).unlink(missing_ok=True)
    print(f"  saved: {out_path.name}")


def dark_documentary():
    """Deep drone with dissonant overtones and slow LFO pulse — tense and cinematic."""
    t = np.linspace(0, DURATION, SR * DURATION, endpoint=False)

    # Root A1 drone + E2 fifth + Bb1 tritone (the "evil" interval)
    audio = (
        0.38 * np.sin(2 * np.pi * 55.0  * t) +   # A1 root
        0.22 * np.sin(2 * np.pi * 82.5  * t) +   # E2 fifth
        0.12 * np.sin(2 * np.pi * 110.0 * t) +   # A2 octave
        0.10 * np.sin(2 * np.pi * 58.27 * t) +   # Bb1 tritone — the dissonance
        0.06 * np.sin(2 * np.pi * 146.8 * t) +   # D3 minor third
        0.04 * np.sin(2 * np.pi * 220.0 * t)     # A3 harmonic shimmer
    )

    # Two LFOs: slow breathing + medium tension pulse
    lfo_slow  = 0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t)
    lfo_mid   = 0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * t)
    audio *= (0.65 + 0.22 * lfo_slow + 0.13 * lfo_mid)

    # Subtle low thud every ~4 seconds
    thud_freq = 0.25
    thud_env  = np.maximum(0, np.sin(2 * np.pi * thud_freq * t)) ** 12
    thud      = 0.12 * thud_env * np.sin(2 * np.pi * 40 * t)
    audio    += thud

    return _fade(audio)


def gentle_reverent():
    """Warm minor-key pad with slow chord movement — contemplative and warm."""
    t = np.linspace(0, DURATION, SR * DURATION, endpoint=False)

    # D minor feel: D2, A2, F2, C3
    chord = (
        0.28 * np.sin(2 * np.pi * 73.4  * t) +   # D2
        0.22 * np.sin(2 * np.pi * 110.0 * t) +   # A2
        0.18 * np.sin(2 * np.pi * 87.3  * t) +   # F2
        0.14 * np.sin(2 * np.pi * 130.8 * t) +   # C3
        0.10 * np.sin(2 * np.pi * 146.8 * t) +   # D3 octave
        0.08 * np.sin(2 * np.pi * 220.0 * t)     # A3 shimmer
    )

    # Very slow swell
    swell = 0.55 + 0.45 * np.sin(2 * np.pi * 0.06 * t + np.pi / 3)
    audio = chord * swell

    # Gentle high bell ping every ~8 seconds
    bell_t = t % 8.0
    bell_env = np.exp(-bell_t * 1.8)
    bell = 0.07 * bell_env * np.sin(2 * np.pi * 880 * t)
    audio += bell

    return _fade(audio)


def upbeat_news():
    """Punchy, modern, forward-motion. Brisk and clean."""
    t = np.linspace(0, DURATION, SR * DURATION, endpoint=False)

    # Clean major feel: G2, D3, B2, E3
    pad = (
        0.20 * np.sin(2 * np.pi * 98.0  * t) +   # G2
        0.18 * np.sin(2 * np.pi * 146.8 * t) +   # D3
        0.16 * np.sin(2 * np.pi * 123.5 * t) +   # B2
        0.12 * np.sin(2 * np.pi * 164.8 * t) +   # E3
        0.10 * np.sin(2 * np.pi * 196.0 * t) +   # G3 shimmer
        0.08 * np.sin(2 * np.pi * 293.7 * t)     # D4 top note
    )

    # Rhythmic gate at 2 beats/sec
    gate = (np.sin(2 * np.pi * 2.0 * t) > 0).astype(float)
    gate = np.convolve(gate, np.ones(int(SR * 0.08)) / int(SR * 0.08), mode='same')
    gate = 0.6 + 0.4 * gate

    audio = pad * gate

    # Punchy kick-like sub every beat
    kick_env = np.exp(-(t % 0.5) * 18)
    kick = 0.15 * kick_env * np.sin(2 * np.pi * 60 * t)
    audio += kick

    return _fade(audio)


def whimsical_warm():
    """Gentle bells and warm pad — cozy and friendly."""
    t = np.linspace(0, DURATION, SR * DURATION, endpoint=False)

    # C major feel: C3, E3, G3, C4
    pad = (
        0.22 * np.sin(2 * np.pi * 130.8 * t) +   # C3
        0.18 * np.sin(2 * np.pi * 164.8 * t) +   # E3
        0.16 * np.sin(2 * np.pi * 196.0 * t) +   # G3
        0.12 * np.sin(2 * np.pi * 261.6 * t) +   # C4
        0.08 * np.sin(2 * np.pi * 329.6 * t)     # E4 shimmer
    )

    swell = 0.6 + 0.4 * np.sin(2 * np.pi * 0.10 * t)
    audio = pad * swell

    # Gentle bell arpeggio every 3 seconds
    freqs = [523.25, 659.26, 783.99, 1046.50]  # C5 E5 G5 C6
    for i, freq in enumerate(freqs):
        offset = i * 0.75
        bell_t = (t - offset) % 3.0
        bell_t[bell_t < 0] = 0
        env = np.exp(-bell_t * 4.0) * (t >= offset)
        audio += 0.06 * env * np.sin(2 * np.pi * freq * t)

    return _fade(audio)


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("assets/music")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Generating background music tracks...")
    _to_mp3(dark_documentary(),  out_dir / "dark_documentary.mp3")
    _to_mp3(gentle_reverent(),   out_dir / "gentle_reverent.mp3")
    _to_mp3(upbeat_news(),       out_dir / "upbeat_news.mp3")
    _to_mp3(whimsical_warm(),    out_dir / "whimsical_warm.mp3")
    print("Done.")
