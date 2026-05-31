#!/usr/bin/env python3
"""
OhRight — Orchestrator (main loop)
Ties together all layers:
  1. Fetch raw events from screenpipe API
  2. Extract semantic meaning via OpenAI (Layer 2)
  3. Build and maintain the intent graph (Layer 3)
  4. Run temporal reasoning / attention decay (Layer 4)

Usage:
  python orchestrator.py               Run once then exit
  python orchestrator.py --watch        Run continuously (poll every N minutes)
  python orchestrator.py --interval 10  Poll every 10 minutes
"""

import sys
import os

# === Load keys BEFORE importing modules that cache them ===
_sp_key_file = os.path.expanduser("~/.ohright/.sp_key")
_openai_key_file = os.path.expanduser("~/.ohright/.openai_key")

if not os.environ.get("SCREENPIPE_API_KEY") and os.path.exists(_sp_key_file):
    with open(_sp_key_file) as f:
        os.environ["SCREENPIPE_API_KEY"] = f.read().strip()

if not os.environ.get("OPENAI_API_KEY") and os.path.exists(_openai_key_file):
    with open(_openai_key_file) as f:
        os.environ["OPENAI_API_KEY"] = f.read().strip()

import json
import time
import requests
import argparse
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import init_db, insert_raw_event, get_unprocessed_events, get_recent_semantic_events
from db import get_db
from embeddings import embed_single, embedding_to_blob, check_ollama_available
from extract import extract_semantic_events, extract_with_context
from graph import upsert_node, link_nodes, decay_attention, find_similar_nodes

# Configuration
SCREENPIPE_URL = os.environ.get("SCREENPIPE_URL", "http://localhost:3030")
SCREENPIPE_API_KEY = os.environ.get("SCREENPIPE_API_KEY", "")
POLL_INTERVAL = int(os.environ.get("OHRIGHT_POLL_INTERVAL", "10"))  # minutes
BATCH_SIZE = 100  # max raw events to process per batch


def fetch_screenpipe_events(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """
    Fetch raw events from the screenpipe REST API.
    Returns list of normalized event dicts.
    """
    headers = {}
    if SCREENPIPE_API_KEY:
        headers["Authorization"] = f"Bearer {SCREENPIPE_API_KEY}"

    params = {"limit": limit, "content_type": "all"}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    try:
        resp = requests.get(
            f"{SCREENPIPE_URL}/search",
            params=params,
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        print(f"[ohright] Cannot connect to screenpipe at {SCREENPIPE_URL}")
        print("  Is screenpipe running? Try: npx screenpipe@latest record")
        return []
    except Exception as e:
        print(f"[ohright] Error fetching from screenpipe: {e}")
        return []

    # Normalize screenpipe events into our format
    # screenpipe nests everything under item["content"]
    events = []
    for item in data.get("data", []):
        content = item.get("content", {})
        
        # Determine event type
        sp_type = item.get("type", "OCR")
        type_map = {"OCR": "screen", "Audio": "audio", "UI": "accessibility"}
        event_type = type_map.get(sp_type, "screen")
        
        # Build unique ID from frame_id or timestamp
        unique_id = str(content.get("frame_id", item.get("timestamp", "")))
        
        event = {
            "id": unique_id,
            "event_type": event_type,
            "app_name": content.get("app_name", ""),
            "window_name": content.get("window_name", ""),
            "browser_url": content.get("browser_url", ""),
            "text_content": content.get("text", ""),
            "transcription": content.get("transcription", ""),
            "timestamp": item.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "duration_seconds": content.get("duration_seconds"),
            "metadata": {
                k: v for k, v in item.items()
                if k not in ("content", "type", "timestamp")
            }
        }
        events.append(event)

    return events


def ingest_events(events: list[dict]) -> int:
    """Store raw events in the database. Deduplicates consecutive identical text. Returns count of new events."""
    count = 0
    last_text = None
    last_app = None
    for event in events:
        # Skip consecutive identical frames (same app + same text = idle screen)
        current_text = event.get("text_content", "")
        current_app = event.get("app_name", "")
        if current_text == last_text and current_app == last_app and current_text:
            continue
        last_text = current_text
        last_app = current_app
        
        row_id = insert_raw_event(event)
        if row_id:
            count += 1
    return count


def process_pending_events() -> list[dict]:
    """
    Process unprocessed raw events through the LLM extraction pipeline.
    Returns the extracted semantic events.
    """
    raw_events = get_unprocessed_events(limit=BATCH_SIZE)
    if not raw_events:
        return []

    print(f"[ohright] Processing {len(raw_events)} new raw events...")

    # Get recent context for momentum detection
    recent_semantic = get_recent_semantic_events(hours=6, limit=20)

    # Extract semantic events via OpenAI
    if recent_semantic:
        semantic_events = extract_with_context(raw_events, recent_semantic)
    else:
        semantic_events = extract_semantic_events(raw_events)

    if not semantic_events:
        print("[ohright] No semantic events extracted.")
        return []

    # Store semantic events and update graph
    db = get_db()
    for se in semantic_events:
        raw_ids = json.dumps(se.get("raw_event_ids", []))
        category = se.get("category", "other")
        topic = se.get("topic", "")
        intensity = se.get("intensity", 0.5)
        confidence = se.get("confidence", 0.5)
        summary = se.get("summary", "")
        start_time = se.get("start_time", datetime.now(timezone.utc).isoformat())
        end_time = se.get("end_time", start_time)

        # Generate embedding (skip if Ollama busy — optional)
        embedding_text = f"{category}: {topic}: {summary}"
        emb = None
        try:
            if check_ollama_available():
                emb = embedding_to_blob(embed_single(embedding_text))
        except Exception:
            pass

        db.execute("""
            INSERT INTO semantic_events
                (category, topic, subcategory, intensity, confidence,
                 summary, raw_event_ids, embedding, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            category, topic, se.get("subcategory", ""), intensity, confidence,
            summary, raw_ids, emb, start_time, end_time
        ))

    # Commit and close DB before graph updates (graph opens its own connections)
    db.commit()
    db.close()

    # Now update intent graph — each function opens its own DB connection
    for se in semantic_events:
        category = se.get("category", "other")
        topic = se.get("topic", "")
        intensity = se.get("intensity", 0.5)
        confidence = se.get("confidence", 0.5)
        summary = se.get("summary", "")

        node_id = upsert_node(
            node_type=_map_category_to_node_type(category),
            label=topic or summary[:80],
            description=summary,
            attention_delta=intensity * confidence,
            dwell_seconds=_estimate_dwell(raw_events, se.get("raw_event_ids", [])),
        )

        # Find similar existing nodes and link them
        if topic:
            similar = find_similar_nodes(topic, limit=3, min_similarity=0.65)
            for sim_node in similar:
                if sim_node["id"] != node_id:
                    link_nodes(node_id, sim_node["id"], "related_to", weight=sim_node.get("similarity", 0.5))

    print(f"[ohright] Extracted {len(semantic_events)} semantic events, updated graph.")
    return semantic_events


def _map_category_to_node_type(category: str) -> str:
    """Map semantic event category to intent graph node type."""
    mapping = {
        "product_research": "product",
        "technical_debugging": "workflow",
        "learning": "interest",
        "content_consumption": "interest",
        "deep_work": "project",
        "communication": "workflow",
        "planning": "project",
        "travel_planning": "interest",
        "job_research": "interest",
        "startup_ideation": "project",
        "finance": "habit",
        "health": "habit",
        "entertainment": "interest",
        "administrative": "workflow",
    }
    return mapping.get(category, "interest")


def _estimate_dwell(raw_events: list[dict], event_ids: list[int]) -> float:
    """Estimate dwell time in seconds from a set of raw event timestamps."""
    matching = [e for e in raw_events if e.get("id") in event_ids]
    if len(matching) < 2:
        return 0.0

    timestamps = []
    for e in matching:
        ts_str = e.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            timestamps.append(ts)
        except (ValueError, TypeError):
            continue

    if len(timestamps) < 2:
        return 0.0

    timestamps.sort()
    return (timestamps[-1] - timestamps[0]).total_seconds()


def run_once():
    """Run one full cycle: fetch → process → graph update → decay."""
    print(f"\n[ohright] ── Cycle started at {datetime.now().strftime('%H:%M:%S')} ──")

    # Check prerequisites
    if not check_ollama_available():
        print("[ohright] WARNING: Ollama not available. Embeddings will fail.")
        print("  Run: ollama pull gte-small && ollama serve")

    if not os.environ.get("OPENAI_API_KEY"):
        print("[ohright] WARNING: OPENAI_API_KEY not set. Semantic extraction will fail.")
        print("  Set: export OPENAI_API_KEY=sk-...")

    # 1. Fetch events from screenpipe
    events = fetch_screenpipe_events(limit=BATCH_SIZE)
    if events:
        new_count = ingest_events(events)
        print(f"[ohright] Ingested {new_count} new events (from {len(events)} fetched).")

    # 2. Process pending events through LLM
    semantic = process_pending_events()

    # 3. Run attention decay
    decay_attention()

    # 4. Summary
    print(f"[ohright] Cycle complete. Events: {len(events)} fetched, {len(semantic)} semantic events extracted.")
    print(f"[ohright] ────────────────────────────────")


def run_watch(interval_minutes: int = 10):
    """Run continuously, polling every N minutes."""
    print(f"[ohright] Watching — polling every {interval_minutes} minutes. Ctrl+C to stop.")
    print(f"[ohright] screenpipe: {SCREENPIPE_URL}")
    print()

    try:
        while True:
            run_once()
            print(f"\n[ohright] Sleeping {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)
    except KeyboardInterrupt:
        print("\n[ohright] Stopped.")


def main():
    init_db()

    parser = argparse.ArgumentParser(description="OhRight — semantic memory layer orchestrator")
    parser.add_argument("--watch", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL,
                        help=f"Poll interval in minutes (default: {POLL_INTERVAL})")
    args = parser.parse_args()

    if args.watch:
        run_watch(interval_minutes=args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
