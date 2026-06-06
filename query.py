#!/usr/bin/env python3
"""
OhRight Query API — JSON interface for menu bar app and Raycast

Usage:
  python3 query.py obsessions          # Top interests (JSON)
  python3 query.py products            # Product research (JSON)
  python3 query.py abandoned           # Dropped projects (JSON)
  python3 query.py context [time]      # What was I doing (JSON)
  python3 query.py search "monitors"   # Semantic search (JSON)
  python3 query.py smart_search "tell me what I almost bought"  # NL search (JSON)
  python3 query.py screen_time         # Time by category today (JSON)
  python3 query.py recent              # Recent activity (last hour)
  python3 query.py stats               # Dashboard stats
  python3 query.py all                 # Full graph snapshot
  python3 query.py raycast             # Single endpoint for Raycast script filter

Output: JSON to stdout.
"""

import sys
import os
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import init_db, get_db
from graph import get_top_nodes, get_abandoned_nodes, find_similar_nodes


# -- User-friendly category labels --
CATEGORY_LABELS = {
    "product_research": "Shopping",
    "purchase_intent": "Shopping",
    "technical_debugging": "Coding",
    "learning": "Learning",
    "content_consumption": "Browsing",
    "media_consumption": "Media",
    "deep_work": "Coding",
    "communication": "Messaging",
    "planning": "Productivity",
    "travel_planning": "Travel",
    "job_research": "Career",
    "startup_ideation": "Projects",
    "finance": "Finance",
    "health": "Health",
    "entertainment": "Entertainment",
    "administrative": "System",
    "recurring_behavior": "Habits",
    # Node types (for backward compat with old data)
    "shopping": "Shopping",
    "coding": "Coding",
    "browsing": "Browsing",
    "media": "Media",
    "messaging": "Messaging",
    "productivity": "Productivity",
    "travel": "Travel",
    "career": "Career",
    "projects": "Projects",
    "habits": "Habits",
    "system": "System",
    # Legacy node types
    "product": "Shopping",
    "project": "Projects",
    "interest": "Interests",
    "workflow": "Productivity",
    "habit": "Habits",
}

CATEGORY_ICONS = {
    "Shopping": "cart",
    "Coding": "laptopcomputer",
    "Learning": "book",
    "Browsing": "globe",
    "Media": "play.circle",
    "Messaging": "bubble.left",
    "Productivity": "checklist",
    "Travel": "airplane",
    "Career": "briefcase",
    "Projects": "hammer",
    "Finance": "dollarsign.circle",
    "Health": "heart",
    "Entertainment": "gamecontroller",
    "System": "gearshape",
    "Habits": "repeat",
    "Interests": "star",
}


def friendly_type(raw_type: str) -> str:
    """Convert raw category/node_type to user-friendly label."""
    return CATEGORY_LABELS.get(raw_type, raw_type.replace("_", " ").title())


def get_best_url(label: str, node_type: str = "") -> str:
    """
    Find the best browser URL for a given topic/node.
    Joins intent_nodes -> semantic_events -> raw_events to find source URLs.
    """
    db = get_db()
    try:
        rows = db.execute("""
            SELECT re.browser_url
            FROM semantic_events se
            JOIN raw_events re ON (
                se.raw_event_ids LIKE ('%' || re.id || '%')
                OR se.raw_event_ids LIKE ('%' || re.screenpipe_id || '%')
            )
            WHERE se.topic LIKE ?
            AND re.browser_url IS NOT NULL
            AND re.browser_url != ''
            ORDER BY se.intensity DESC, re.timestamp DESC
            LIMIT 1
        """, (f"%{label[:60]}%",)).fetchall()

        if rows:
            return rows[0]["browser_url"]

        # Fallback: search by description match
        rows = db.execute("""
            SELECT re.browser_url
            FROM semantic_events se
            JOIN raw_events re ON (
                se.raw_event_ids LIKE ('%' || re.id || '%')
                OR se.raw_event_ids LIKE ('%' || re.screenpipe_id || '%')
            )
            WHERE se.summary LIKE ?
            AND re.browser_url IS NOT NULL
            AND re.browser_url != ''
            ORDER BY se.intensity DESC
            LIMIT 1
        """, (f"%{label[:60]}%",)).fetchall()

        if rows:
            return rows[0]["browser_url"]
    finally:
        db.close()

    return ""


def enrich_with_url(item: dict) -> dict:
    """Add best URL to a result item if available."""
    title = item.get("title", "")
    if title and not item.get("url"):
        url = get_best_url(title)
        if url:
            item["url"] = url
    return item


def _serialize(obj):
    """JSON serializer for datetime and bytes."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return None
    return str(obj)


def _format_dwell(seconds: float) -> str:
    """Human-readable dwell time."""
    hours = seconds / 3600
    if hours >= 1:
        return f"{hours:.1f}h"
    minutes = seconds / 60
    if minutes >= 1:
        return f"{minutes:.0f}m"
    return f"{seconds:.0f}s"


def cmd_obsessions(limit=10):
    """Top current interests."""
    nodes = get_top_nodes(limit=limit, min_attention=0.05, status="active")
    results = []
    for n in nodes:
        desc = n.get("description", "") or ""
        item = {
            "title": n["label"],
            "subtitle": desc[:100],
            "type": friendly_type(n["node_type"]),
            "time_spent": _format_dwell(n["total_dwell_seconds"]),
            "revisits": n["revisit_count"],
            "last_seen": n.get("last_seen", "")[:10],
            "status": n.get("status", "active"),
        }
        results.append(enrich_with_url(item))
    return results


def cmd_products(limit=15):
    """Products researched."""
    db = get_db()
    # Search for both old "product" and new "shopping" types
    rows = db.execute("""
        SELECT * FROM intent_nodes
        WHERE node_type IN ('product', 'shopping')
        ORDER BY attention_score DESC LIMIT ?
    """, (limit,)).fetchall()
    db.close()

    results = []
    for r in rows:
        n = dict(r)
        desc = n.get("description", "") or ""
        item = {
            "title": n["label"],
            "subtitle": desc[:100],
            "type": "Shopping",
            "status": n.get("status", "active"),
            "time_spent": _format_dwell(n["total_dwell_seconds"]),
            "revisits": n["revisit_count"],
            "last_seen": n.get("last_seen", "")[:10],
        }
        results.append(enrich_with_url(item))
    return results


def cmd_abandoned(limit=15):
    """Projects and ideas that were dropped."""
    nodes = get_abandoned_nodes(limit=limit)
    results = []
    for n in nodes:
        desc = n.get("description", "") or ""
        item = {
            "title": n["label"],
            "subtitle": desc[:100],
            "type": friendly_type(n["node_type"]),
            "first_seen": n.get("first_seen", "")[:10],
            "last_seen": n.get("last_seen", "")[:10],
            "time_spent": _format_dwell(n["total_dwell_seconds"]),
        }
        results.append(enrich_with_url(item))
    return results


def cmd_context():
    """Current context snapshot."""
    active = get_top_nodes(limit=5, min_attention=0.05)
    abandoned = get_abandoned_nodes(limit=3)

    return {
        "active_topics": [
            {"label": n["label"], "type": friendly_type(n["node_type"])}
            for n in active
        ],
        "recently_dropped": [
            {"label": n["label"], "last_seen": n.get("last_seen", "")[:10]}
            for n in abandoned[:3]
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def cmd_search(query, limit=10):
    """Semantic search over the behavioral graph."""
    nodes = find_similar_nodes(query, limit=limit, min_similarity=0.2)
    results = []
    for n in nodes:
        desc = n.get("description", "") or ""
        item = {
            "title": n["label"],
            "subtitle": desc[:100],
            "type": friendly_type(n["node_type"]),
            "status": n.get("status", "active"),
            "time_spent": _format_dwell(n.get("total_dwell_seconds", 0)),
            "revisits": n.get("revisit_count", 0),
        }
        results.append(enrich_with_url(item))
    return results


def cmd_smart_search(query, limit=10):
    """Natural language search — understands intent and routes to the right data."""
    # Try to use ask.py's NL understanding
    try:
        from ask import understand_query, execute_action
        action = understand_query(query)
        data = execute_action(action)
        message = action.get("message", "")

        # Return structured JSON for the Swift app
        if isinstance(data, list):
            return {
                "message": message,
                "results": data[:limit],
            }
        elif isinstance(data, dict):
            return {
                "message": message,
                "results": data,
            }
    except Exception:
        pass

    # Fallback: regular vector search
    results = cmd_search(query, limit=limit)
    return {
        "message": f'Results for "{query}":',
        "results": results,
    }


def cmd_screen_time(period="today"):
    """Aggregate time spent by category from semantic events."""
    db = get_db()

    if period == "week":
        since = (datetime.now() - timedelta(days=7)).isoformat()
    else:
        since = (datetime.now() - timedelta(hours=24)).isoformat()

    # Aggregate from semantic_events
    rows = db.execute("""
        SELECT category,
               COUNT(*) as event_count,
               SUM(CASE
                   WHEN end_time IS NOT NULL AND start_time IS NOT NULL
                   THEN (julianday(end_time) - julianday(start_time)) * 24 * 60
                   ELSE 5
               END) as total_minutes
        FROM semantic_events
        WHERE start_time >= ?
        GROUP BY category
        ORDER BY total_minutes DESC
    """, (since,)).fetchall()

    # Also get from intent_nodes dwell time for richer data
    node_rows = db.execute("""
        SELECT node_type,
               COUNT(*) as topic_count,
               SUM(total_dwell_seconds) / 60.0 as total_minutes
        FROM intent_nodes
        WHERE last_seen >= ?
        AND status = 'active'
        GROUP BY node_type
        ORDER BY total_minutes DESC
    """, (since,)).fetchall()
    db.close()

    # Merge both sources, preferring semantic_events
    categories = {}
    for r in rows:
        label = friendly_type(r["category"])
        mins = round(r["total_minutes"] or 0, 1)
        if label in categories:
            categories[label]["minutes"] += mins
            categories[label]["events"] += r["event_count"]
        else:
            categories[label] = {
                "category": label,
                "minutes": mins,
                "events": r["event_count"],
            }

    # Fill in from node dwell times if not already covered
    for r in node_rows:
        label = friendly_type(r["node_type"])
        mins = round(r["total_minutes"] or 0, 1)
        if label not in categories:
            categories[label] = {
                "category": label,
                "minutes": mins,
                "events": r["topic_count"],
            }

    # Sort and format
    sorted_cats = sorted(categories.values(), key=lambda x: x["minutes"], reverse=True)
    total_minutes = sum(c["minutes"] for c in sorted_cats)

    for c in sorted_cats:
        hours = c["minutes"] / 60
        c["hours"] = round(hours, 1)
        c["display"] = f"{hours:.1f}h" if hours >= 1 else f"{c['minutes']:.0f}m"
        c["percentage"] = round(c["minutes"] / total_minutes * 100, 1) if total_minutes > 0 else 0

    return {
        "period": period,
        "total_hours": round(total_minutes / 60, 1),
        "categories": sorted_cats,
    }


def cmd_recent(hours=1):
    """Recent semantic events from the last N hours."""
    db = get_db()
    rows = db.execute("""
        SELECT category, topic, summary, intensity, created_at
        FROM semantic_events
        WHERE created_at > datetime('now', ?)
        ORDER BY created_at DESC LIMIT 20
    """, (f"-{hours} hours",)).fetchall()
    db.close()

    return [
        {
            "title": r["topic"] or (r["summary"] or "")[:60],
            "subtitle": (r["summary"] or "")[:100],
            "type": friendly_type(r["category"]),
            "time": r["created_at"],
        }
        for r in rows
    ]


def cmd_stats():
    """Dashboard-friendly stats."""
    db = get_db()
    total_topics = db.execute("SELECT COUNT(*) as c FROM intent_nodes").fetchone()["c"]
    total_events = db.execute("SELECT COUNT(*) as c FROM raw_events").fetchone()["c"]
    total_insights = db.execute("SELECT COUNT(*) as c FROM semantic_events").fetchone()["c"]

    active = db.execute("SELECT COUNT(*) as c FROM intent_nodes WHERE status='active'").fetchone()["c"]
    dormant = db.execute("SELECT COUNT(*) as c FROM intent_nodes WHERE status='dormant'").fetchone()["c"]
    abandoned = db.execute("SELECT COUNT(*) as c FROM intent_nodes WHERE status='abandoned'").fetchone()["c"]

    types = db.execute("""
        SELECT node_type, COUNT(*) as c FROM intent_nodes GROUP BY node_type ORDER BY c DESC
    """).fetchall()
    db.close()

    return {
        "topics_tracked": total_topics,
        "active": active,
        "sleeping": dormant,
        "dropped": abandoned,
        "captures": total_events,
        "insights": total_insights,
        "categories": {friendly_type(t["node_type"]): t["c"] for t in types},
    }


def cmd_all():
    """Full graph snapshot."""
    db = get_db()
    nodes = [dict(r) for r in db.execute("SELECT * FROM intent_nodes ORDER BY attention_score DESC").fetchall()]
    edges = [dict(r) for r in db.execute("SELECT * FROM intent_edges ORDER BY weight DESC LIMIT 50").fetchall()]
    db.close()

    for n in nodes:
        n.pop("embedding", None)
        n.pop("metadata_json", None)
    for e in edges:
        e.pop("metadata_json", None)

    return {"nodes": nodes, "edges": edges}


def cmd_raycast(query=""):
    """Single endpoint for Raycast script filter."""
    items = []

    if not query:
        obsessions = cmd_obsessions(limit=5)
        items = [
            {
                "title": o["title"],
                "subtitle": f"{o['type']} — {o.get('time_spent', '')} — {o.get('subtitle', '')}",
                "arg": f"ohright://node/{o['title']}",
                "icon": {"path": "./icons/graph.png"}
            }
            for o in obsessions
        ]
    else:
        results = cmd_search(query, limit=8)
        items = [
            {
                "title": r["title"],
                "subtitle": f"{r['type']} — {r.get('subtitle', '')}",
                "arg": f"ohright://search/{r['title']}",
            }
            for r in results
        ]

    return {"items": items}


def main():
    init_db()

    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: query.py <command> [args]",
                          "commands": ["obsessions", "products", "abandoned", "context",
                                       "search", "smart_search", "screen_time",
                                       "recent", "stats", "all", "raycast"]}, indent=2))
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "obsessions": lambda: cmd_obsessions(),
        "products": lambda: cmd_products(),
        "abandoned": lambda: cmd_abandoned(),
        "context": lambda: cmd_context(),
        "search": lambda: cmd_search(args[0] if args else ""),
        "smart_search": lambda: cmd_smart_search(args[0] if args else ""),
        "screen_time": lambda: cmd_screen_time(args[0] if args else "today"),
        "recent": lambda: cmd_recent(int(args[0]) if args else 1),
        "stats": lambda: cmd_stats(),
        "all": lambda: cmd_all(),
        "raycast": lambda: cmd_raycast(args[0] if args else ""),
    }

    if cmd not in commands:
        print(json.dumps({"error": f"Unknown command: {cmd}",
                          "available": list(commands.keys())}))
        sys.exit(1)

    result = commands[cmd]()
    print(json.dumps(result, indent=2, default=_serialize))


if __name__ == "__main__":
    main()
