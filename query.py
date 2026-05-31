#!/usr/bin/env python3
"""
OhRight Query API — Raycast-ready JSON interface

Usage:
  python3 query.py obsessions          # Top interests (JSON)
  python3 query.py products            # Product research (JSON)
  python3 query.py abandoned           # Dropped projects (JSON)
  python3 query.py context [time]      # What was I doing (JSON)
  python3 query.py search "monitors"   # Semantic search (JSON)
  python3 query.py recent              # Recent activity (last hour)
  python3 query.py all                 # Full graph snapshot
  python3 query.py raycast             # Single endpoint for Raycast script filter

Output: JSON to stdout, ready for Raycast script filter or any automation.
"""

import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import init_db, get_db
from graph import get_top_nodes, get_abandoned_nodes, find_similar_nodes


def get_best_url(label: str, node_type: str = "") -> str:
    """
    Find the best browser URL for a given topic/node.
    Joins intent_nodes → semantic_events → raw_events to find source URLs.
    """
    db = get_db()
    try:
        # Find semantic events whose topic matches this node's label
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
        return None  # skip blob data
    return str(obj)


def cmd_obsessions(limit=10):
    """Top current interests with attention scores."""
    nodes = get_top_nodes(limit=limit, min_attention=0.05, status="active")
    results = []
    for n in nodes:
        item = {
            "title": n["label"],
            "subtitle": f"{n['node_type']} — attention: {n['attention_score']:.0%} — {n.get('description', '')[:80]}",
            "type": n["node_type"],
            "attention": round(n["attention_score"], 3),
            "revisits": n["revisit_count"],
            "last_seen": n.get("last_seen", "")[:10],
            "dwell_hours": round(n["total_dwell_seconds"] / 3600, 1),
        }
        results.append(enrich_with_url(item))
    return results


def cmd_products(limit=15):
    """Products researched, with purchase intent signals."""
    db = get_db()
    rows = db.execute("""
        SELECT * FROM intent_nodes
        WHERE node_type = 'product'
        ORDER BY attention_score DESC LIMIT ?
    """, (limit,)).fetchall()
    db.close()
    
    results = []
    for r in rows:
        n = dict(r)
        status_emoji = {"active": "🔄", "dormant": "💤", "abandoned": "❌"}.get(n.get("status", ""), "")
        item = {
            "title": n["label"],
            "subtitle": f"{status_emoji} {n.get('status', 'active')} — {n['attention_score']:.0%} attention — {n.get('description', '')[:80]}",
            "type": "product",
            "attention": round(n["attention_score"], 3),
            "revisits": n["revisit_count"],
            "status": n.get("status", "active"),
            "dwell_hours": round(n["total_dwell_seconds"] / 3600, 1),
        }
        results.append(enrich_with_url(item))
    return results


def cmd_abandoned(limit=15):
    """Projects and ideas that were dropped."""
    nodes = get_abandoned_nodes(limit=limit)
    results = []
    for n in nodes:
        item = {
            "title": n["label"],
            "subtitle": f"Dropped — peak attention was {n['attention_score']:.0%} — {n.get('description', '')[:80]}",
            "type": n["node_type"],
            "attention": round(n["attention_score"], 3),
            "first_seen": n.get("first_seen", "")[:10],
            "last_seen": n.get("last_seen", "")[:10],
            "dwell_hours": round(n["total_dwell_seconds"] / 3600, 1),
        }
        results.append(enrich_with_url(item))
    return results


def cmd_context():
    """Current context snapshot."""
    active = get_top_nodes(limit=5, min_attention=0.05)
    abandoned = get_abandoned_nodes(limit=3)
    
    return {
        "active_topics": [
            {"label": n["label"], "type": n["node_type"], "attention": round(n["attention_score"], 3)}
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
        item = {
            "title": n["label"],
            "subtitle": f"{n['node_type']} — match: {n.get('similarity', 0):.0%} — {n.get('description', '')[:80]}",
            "type": n["node_type"],
            "match": round(n.get("similarity", 0), 3),
            "attention": round(n["attention_score"], 3),
        }
        results.append(enrich_with_url(item))
    return results


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
            "title": r["topic"] or r["summary"][:60],
            "subtitle": f"{r['category']} — intensity: {r['intensity']:.0%}",
            "type": r["category"],
            "intensity": round(r["intensity"], 3),
            "time": r["created_at"],
        }
        for r in rows
    ]


def cmd_stats():
    """Graph analytics."""
    db = get_db()
    total_nodes = db.execute("SELECT COUNT(*) as c FROM intent_nodes").fetchone()["c"]
    total_edges = db.execute("SELECT COUNT(*) as c FROM intent_edges").fetchone()["c"]
    total_events = db.execute("SELECT COUNT(*) as c FROM raw_events").fetchone()["c"]
    total_semantic = db.execute("SELECT COUNT(*) as c FROM semantic_events").fetchone()["c"]
    
    active = db.execute("SELECT COUNT(*) as c FROM intent_nodes WHERE status='active'").fetchone()["c"]
    dormant = db.execute("SELECT COUNT(*) as c FROM intent_nodes WHERE status='dormant'").fetchone()["c"]
    abandoned = db.execute("SELECT COUNT(*) as c FROM intent_nodes WHERE status='abandoned'").fetchone()["c"]
    
    types = db.execute("""
        SELECT node_type, COUNT(*) as c FROM intent_nodes GROUP BY node_type ORDER BY c DESC
    """).fetchall()
    db.close()
    
    return {
        "graph": {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "active": active,
            "dormant": dormant,
            "abandoned": abandoned,
        },
        "events": {
            "raw": total_events,
            "semantic": total_semantic,
        },
        "types": {t["node_type"]: t["c"] for t in types},
    }


def cmd_all():
    """Full graph snapshot — all nodes with their data."""
    db = get_db()
    nodes = [dict(r) for r in db.execute("SELECT * FROM intent_nodes ORDER BY attention_score DESC").fetchall()]
    edges = [dict(r) for r in db.execute("SELECT * FROM intent_edges ORDER BY weight DESC LIMIT 50").fetchall()]
    db.close()
    
    # Strip blobs
    for n in nodes:
        n.pop("embedding", None)
        n.pop("metadata_json", None)
    for e in edges:
        e.pop("metadata_json", None)
    
    return {"nodes": nodes, "edges": edges}


def cmd_raycast(query=""):
    """
    Single endpoint for Raycast script filter.
    Returns formatted items Raycast can display directly.
    """
    items = []
    
    if not query:
        # Default: show obsessions
        obsessions = cmd_obsessions(limit=5)
        items = [
            {
                "title": f"🔥 {o['title']}",
                "subtitle": o["subtitle"],
                "arg": f"ohright://node/{o['title']}",
                "icon": {"path": "./icons/graph.png"}
            }
            for o in obsessions
        ]
    else:
        # Search mode
        results = cmd_search(query, limit=8)
        items = [
            {
                "title": r["title"],
                "subtitle": r["subtitle"],
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
                                      "search", "recent", "stats", "all", "raycast"]}, indent=2))
        sys.exit(1)
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    commands = {
        "obsessions": lambda: cmd_obsessions(),
        "products": lambda: cmd_products(),
        "abandoned": lambda: cmd_abandoned(),
        "context": lambda: cmd_context(),
        "search": lambda: cmd_search(args[0] if args else ""),
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
