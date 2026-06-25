# The Marquee — Daily Entertainment Shorts Bot

Automatically pulls a real trending celebrity/pop-culture story each day,
writes an original ~50-second recap (Claude), builds a vertical video with
real stock footage, and uploads it to YouTube. Same automation pattern as
the news/finance/sports channels — real current events, not invented content.

---

## Why this one has extra guardrails

Celebrity news involves real, named people, and the genre is full of
unverified rumors and gossip-mill speculation. The system prompt in
`generate_script.py` is deliberately stricter here than the other channels:

- Never fabricates or embellishes a quote — only reports something as said
  if the source clearly reports it that way.
- If the source hedges ("reportedly," "alleged," "according to sources"),
  the script keeps that hedge — a rumor never gets upgraded into a stated fact.
- No speculation about private lives, relationships, or motivations beyond
  what's publicly confirmed in the source.
- Neutral, observational tone — not mocking or gossipy.

This matters practically, not just ethically: a channel that states rumors
as fact gets called out in comments fast, and it's the kind of thing that
erodes trust (and can invite legal risk) quicker than almost any other
content mistake. Worth spot-checking outputs periodically regardless.

---

## What this actually does (and doesn't do)

- ✅ Pulls a real trending story from Google News' Entertainment section feed
  each day and writes an original recap — same "real news, original words"
  pattern as Pulse Brief and The Buzzer.
- ✅ Real stock-footage clips (red carpet, premieres, awards shows — generic
  b-roll, not footage of the actual people involved) cut between scenes.
- ❌ Does **not** guarantee 100k subscribers in a month, or any subscriber
  count — no content strategy can promise that, automated or not.
- ❌ Does **not** write misleading titles/thumbnails — compelling, not
  deceptive. Misleading metadata is also a real YouTube policy risk, not
  just a trust issue.

---

## Setup

Same pattern as your other news-style channels (Pulse Brief, The Uptick,
The Buzzer) — reuse `ANTHROPIC_API_KEY` and `YT_API_KEY` as-is, new
`YT_REFRESH_TOKEN` for this channel's account, `PEXELS_API_KEY` optional
(falls back to a gradient background if unset).

### Step 1: YouTube OAuth

```powershell
$env:YT_CLIENT_ID = "your-client-id"
$env:YT_CLIENT_SECRET = "your-client-secret"
venv\Scripts\python.exe scripts\get_oauth_token.py
```

Log into *this* channel's Google account when the browser opens.

### Step 2: Push to GitHub and add secrets

New repo, push this folder in, then add these repo secrets:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | reuse existing |
| `YT_CLIENT_ID` / `YT_CLIENT_SECRET` | reuse existing |
| `YT_REFRESH_TOKEN` | new, from Step 1 |
| `YT_API_KEY` | optional, for trending-tag enrichment |
| `PEXELS_API_KEY` | optional, for real footage instead of gradient |

### Step 3: Test it

Actions tab → "The Marquee - Daily Entertainment Trend" → **Run workflow**.
Check the result in YouTube Studio before trusting the schedule.

---

## Customizing

- **Topic source**: `NEWS_TOPIC_SECTION: "ENTERTAINMENT"` in `daily-short.yml`
  pulls Google News' whole Entertainment section. Switch to `NEWS_TOPIC_QUERY`
  for something narrower (e.g. just music industry news).
- **Tone/guardrails**: all live in `scripts/generate_script.py`'s system
  prompt — loosen or tighten the hedging/speculation rules there if needed.
- **How videos go public**: `YT_PRIVACY_STATUS` works exactly like the other
  channels — `scheduled` (default), `unlisted`, or `public`.
