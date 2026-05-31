"""
OhRight — Semantic Event Extraction (Layer 2)
Uses OpenAI to classify raw screenpipe events into semantic events.

Input:  batch of raw screenpipe events
Output: structured semantic events with categories, topics, intensity scores
"""

import json
import os
from datetime import datetime, timezone
from openai import OpenAI
from typing import Optional

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OHRIGHT_LLM_MODEL", "gpt-4o-mini")

SEMANTIC_CATEGORIES = [
    "product_research",       # researching products to buy
    "technical_debugging",    # fixing code, errors, infrastructure
    "learning",               # tutorials, docs, courses
    "content_consumption",    # passive browsing, social media, videos
    "deep_work",              # focused coding, writing, designing
    "communication",          # email, slack, messages
    "planning",               # project planning, notes, task management
    "travel_planning",        # researching flights, hotels, destinations
    "job_research",           # looking at jobs, companies, salaries
    "startup_ideation",       # researching markets, competitors, ideas
    "finance",                # banking, investing, budgeting
    "health",                 # fitness, nutrition, medical
    "entertainment",          # games, streaming, music (non-work)
    "administrative",         # settings, updates, file management
    "other"
]

EXTRACTION_PROMPT = """You are an AI that extracts behavioral intent from raw computer activity.

Your job: find what MATTERS to the user — not just what apps they opened.

PRIORITY SIGNALS (hunt for these aggressively):
1. MEDIA CONSUMPTION — songs, playlists, YouTube videos, podcasts, Netflix shows
   → Look for: YouTube/Spotify/Netflix window titles, video names, song names, channel names
   → category: "media_consumption"
   → topic: the specific song, video, podcast name
   → subcategory: "music", "video", "podcast", "streaming"

2. PRODUCT RESEARCH — shopping, comparing products, reading reviews
   → Look for: Amazon/Flipkart, product names, review sites, price comparisons
   → category: "product_research"
   → topic: specific product name
   → subcategory: "electronics", "furniture", "clothing", "software"

3. CONTENT DEEP-DIVE — learning, reading, watching tutorials, researching topics
   → Look for: Wikipedia, docs, blogs, LinkedIn articles, Medium, Substack, tutorials
   → category: "content_consumption"
   → topic: the subject being learned/researched
   → subcategory: "technical", "business", "science", "self_improvement"

4. PURCHASE INTENT — strong buying signals
   → Look for: repeated product page visits, cart pages, checkout, price check
   → category: "purchase_intent"
   → intensity: higher for checkout/cart, lower for first browse
   → topic: product name

5. CREATIVE/PROJECT WORK — building, writing, designing
   → Look for: IDE/code editor content, design tools, writing apps
   → category: "deep_work" 
   → topic: specific project or task (NOT generic app name like "terminal")

6. RECURRING BEHAVIOR — repeated patterns
   → Look for: same song on repeat, same site visited daily, same workflow
   → category: "recurring_behavior"
   → intensity: higher for more repetitions

7. COMMUNICATION (only if topic is clear)
   → Look for: chat messages with clear subjects, meeting topics
   → category: "communication"
   → topic: the conversation subject (NOT just "WhatsApp" or "Slack")

IGNORE:
- Generic terminal windows without clear task context
- System UI (settings, control center, finder)
- App launchers and desktop
- Identical repeated frames with no new information

IMPORTANT: 
- Window titles are the BEST signal — they contain YouTube video names, Spotify song titles, article headlines, product names
- If you see a repeating window title like "Diljit Dosanjh - Lover (Official Video)" → that's a song the user is looping
- If a window title says "Best Ultrawide Monitors 2026" → that's product research
- If you see "linkedin.com/feed" or LinkedIn window titles → extract the content being viewed
- NEVER return generic topics like "tmux sessions" or "terminal usage" — those are useless

Return ONLY valid JSON:
{{
  "semantic_events": [
    {{
      "category": "media_consumption",
      "topic": "Diljit Dosanjh - Lover",
      "subcategory": "music",
      "intensity": 0.9,
      "confidence": 0.85,
      "summary": "Looped this song multiple times while coding — strong preference signal",
      "raw_event_ids": [1, 3, 5],
      "start_time": "2026-05-31T10:00:00Z",
      "end_time": "2026-05-31T11:30:00Z"
    }}
  ]
}}

If no meaningful behavioral patterns found, return empty array: {{"semantic_events": []}}
"""


def format_raw_events_for_llm(events: list[dict]) -> str:
    """Format raw screenpipe events into a concise text block for the LLM."""
    lines = []
    for e in events:
        ts = e.get("timestamp", "")[:19]
        app = e.get("app_name", "unknown")
        window = e.get("window_name", "")
        url = e.get("browser_url", "")
        text = (e.get("text_content") or e.get("transcription") or "")[:200]

        parts = [f"[id={e['id']}] {ts} | {app}"]
        if window:
            parts.append(f" | window: {window[:80]}")
        if url:
            parts.append(f" | url: {url[:100]}")
        if text:
            parts.append(f"\n  text: {text}")

        lines.append("".join(parts))

    return "\n".join(lines)


def extract_semantic_events(
    raw_events: list[dict],
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> list[dict]:
    """
    Send a batch of raw events to OpenAI for semantic classification.
    Returns list of structured semantic event dicts.
    """
    if not raw_events:
        return []

    key = api_key or OPENAI_API_KEY
    if not key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=key)
    model_name = model or OPENAI_MODEL

    formatted = format_raw_events_for_llm(raw_events)
    prompt = EXTRACTION_PROMPT.format(categories=", ".join(SEMANTIC_CATEGORIES))

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Analyze these events:\n\n{formatted}"}
        ],
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    result = json.loads(content)
    return result.get("semantic_events", [])


def extract_with_context(
    raw_events: list[dict],
    recent_semantic_events: list[dict],
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> list[dict]:
    """
    Extract semantic events with awareness of recent context.
    This helps detect recurring patterns and momentum.
    """
    if not raw_events:
        return []

    key = api_key or OPENAI_API_KEY
    if not key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=key)
    model_name = model or OPENAI_MODEL

    formatted = format_raw_events_for_llm(raw_events)

    # Format recent context
    recent_context = "RECENT SEMANTIC EVENTS (for continuity):\n"
    for se in recent_semantic_events[-10:]:
        recent_context += (
            f"- [{se.get('category')}] {se.get('topic')}: "
            f"{se.get('summary', '')}\n"
        )

    prompt = EXTRACTION_PROMPT.format(categories=", ".join(SEMANTIC_CATEGORIES))
    prompt += (
        "\n\nYou also have access to RECENT SEMANTIC EVENTS from earlier today. "
        "Use them to detect recurring patterns, momentum, and topic transitions. "
        "If the user is continuing a previous activity, note it. "
        "If they abruptly switched topics, flag the transition."
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"{recent_context}\n\nNEW RAW EVENTS:\n{formatted}"}
        ],
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    result = json.loads(content)
    return result.get("semantic_events", [])


if __name__ == "__main__":
    # Quick test with mock data
    mock_events = [
        {"id": 1, "timestamp": "2026-05-31T10:00:00Z", "app_name": "Arc",
         "window_name": "Dell U4025QW Ultrawide Monitor Review - YouTube",
         "browser_url": "youtube.com/watch?v=abc123", "text_content": "ultrawide monitor review"},
        {"id": 2, "timestamp": "2026-05-31T10:15:00Z", "app_name": "Arc",
         "window_name": "LG 40WP95C-W vs Dell U4025QW - Reddit",
         "browser_url": "reddit.com/r/ultrawide", "text_content": "comparison thread"},
        {"id": 3, "timestamp": "2026-05-31T10:30:00Z", "app_name": "Arc",
         "window_name": "Best Ultrawide Monitors 2026 - rtings.com",
         "browser_url": "rtings.com/monitor/reviews/best/ultrawide",
         "text_content": "best ultrawide monitors ranked"},
    ]

    print("Testing extraction with mock data...")
    print(format_raw_events_for_llm(mock_events))
    print("\n(This would call OpenAI with the events above)")
