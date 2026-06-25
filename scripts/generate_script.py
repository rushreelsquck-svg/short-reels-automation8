"""
generate_script.py
Turns a raw headline/summary into:
  - an ORIGINAL ~45-55 second narration script (own words, not copied from the source)
  - a title, description, tags, and hashtags for the upload

Keeping this step "in our own words" is what makes the video non-infringing —
we're reporting on a fact, not republishing anyone's article or footage.

Uses forced tool-use (tool_choice) with a strict JSON schema instead of asking
Claude to free-write JSON as text. That guarantees every required field is
always present and correctly typed — the earlier text-based approach
occasionally omitted a field (e.g. "description") since nothing enforced the
shape of plain text output.
"""
import os

import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You write scripts for a daily YouTube Shorts channel called The Marquee,
covering trending celebrity and pop-culture news.

Rules:
- Always rewrite the story in completely original wording. Never copy phrases from the source summary.
- Be factual and neutral. Do not invent details that aren't in the source material.
- NEVER fabricate or embellish a quote. Only state someone said something if the source clearly
  reports them actually saying it. If the source paraphrases rather than quotes, paraphrase too.
- If the source frames something as alleged, rumored, reportedly, or unconfirmed, KEEP that hedging
  in your script — never upgrade a rumor or allegation into a stated fact. When in doubt, hedge more,
  not less.
- Don't speculate about someone's private life, relationships, health, or motivations beyond what's
  publicly confirmed in the source. Report what happened/was said, not guesses about why.
- Neutral, observational tone — not mocking, not gossipy, not snarky about anyone's appearance,
  choices, or personal life. This is a news recap, not commentary.
- Hook viewers in the first 5-7 words with the most attention-grabbing concrete detail (a name, a
  surprising development) — front-load what's actually newsworthy, not a vague tease.
- Hook, then deliver the story, then a one-line close on why people are talking about it.
- The script is spoken aloud, so write for the ear: short sentences, no headers, no bullet points.
- Target 110-130 words (about 45-55 seconds at a natural reading pace).
- The title must be accurate to the content — compelling is good, misleading is not. Lead with the
  person's name if there is one; specific names outperform vague titles for search and discovery.
- Also pick 3-4 short, concrete, visually-literal phrases that a stock-footage search engine could
  find real b-roll for (e.g. "red carpet event", "paparazzi camera flashes", "movie premiere crowd",
  "awards show stage") — these become the background footage, cut together in order, so they should
  roughly follow the story's beats. Never use abstract, non-visual, or text-only phrases. Since these
  are generic stock clips (not actual footage of the people involved), avoid phrases that imply a
  specific named person will appear in the clip.
- Call the submit_video_package tool exactly once with the finished package."""

PACKAGE_TOOL = {
    "name": "submit_video_package",
    "description": "Submit the finished title, script, description, tags, hashtags, and background visual cues for this video.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "<=95 characters, includes a hook, no clickbait that misrepresents the story",
            },
            "script": {
                "type": "string",
                "description": "The spoken narration only, 110-130 words, no headers or bullet points",
            },
            "description": {
                "type": "string",
                "description": "2-4 sentences summarizing the story, plus one line inviting people to follow for daily recaps",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "8-12 lowercase keyword tags relevant to this specific story",
            },
            "hashtags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "5-8 hashtags, each starting with #, relevant to this story; always include #shorts",
            },
            "visual_queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-4 short (2-4 word) concrete, literal stock-footage search phrases for this story's background visuals, in story order",
            },
        },
        "required": ["title", "script", "description", "tags", "hashtags", "visual_queries"],
    },
}


def generate_script_package(topic: dict, trending_keywords: list[str] | None = None) -> dict:
    trending_keywords = trending_keywords or []

    user_prompt = f"""Source headline: {topic['title']}
Source summary: {topic.get('summary', '(no summary available, work from the headline only)')}

Currently-trending YouTube keywords you may draw from IF genuinely relevant (do not force-fit ones that don't fit this story): {", ".join(trending_keywords) if trending_keywords else "(none provided)"}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        tools=[PACKAGE_TOOL],
        tool_choice={"type": "tool", "name": "submit_video_package"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    package = dict(tool_use_block.input)

    # Always guarantee #shorts is present regardless of what the model produced
    if not any(h.lower() == "#shorts" for h in package.get("hashtags", [])):
        package.setdefault("hashtags", []).append("#shorts")

    return package


if __name__ == "__main__":
    import json

    demo_topic = {"title": "Example headline for a dry run", "summary": "Example summary text."}
    print(json.dumps(generate_script_package(demo_topic), indent=2))
