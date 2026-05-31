#!/usr/bin/env python3
"""
OhRight CLI — query your behavioral graph
Usage:
  ohright obsessions         Top current interests/obsessions
  ohright products           Products researched but not purchased
  ohright abandoned          Ideas/projects that were dropped
  ohright context [time]     What was I doing? (default: before lunch)
  ohright recurring          Projects that keep coming back
  ohright graph <query>      Search the graph semantically
  ohright stats              Personal analytics overview
  ohright decay              Run attention decay
"""

import argparse
import sys
import os
import textwrap
from datetime import datetime, timezone, timedelta

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import init_db, get_db
from graph import (
    get_top_nodes, get_abandoned_nodes, find_similar_nodes,
    get_node_with_edges, decay_attention, upsert_node, link_nodes
)


def cmd_obsessions(args):
    """Show current top interests/obsessions."""
    nodes = get_top_nodes(limit=15, min_attention=0.1, status="active")

    if not nodes:
        print("No obsessions detected yet. Keep using your computer — OhRight is learning.")
        return

    print("\n═══ CURRENT OBSESSIONS ═══\n")
    for i, n in enumerate(nodes, 1):
        bar = "█" * int(n["attention_score"] * 20)
        print(f"{i:2}. [{n['node_type']}] {n['label']}")
        print(f"    attention: {bar} {n['attention_score']:.2f}")
        if n.get("description"):
            print(f"    {n['description'][:120]}")
        last = n.get("last_seen", "")[:10]
        print(f"    last seen: {last} | revisits: {n['revisit_count']}")
        print()


def cmd_products(args):
    """Show products researched but not purchased."""
    nodes = get_top_nodes(limit=20, node_type="product", min_attention=0.05)

    if not nodes:
        print("No product research detected yet.")
        return

    print("\n═══ PRODUCTS RESEARCHED ═══\n")
    for i, n in enumerate(nodes, 1):
        status_icon = {"active": "🔄", "dormant": "💤", "abandoned": "❌"}.get(n["status"], "•")
        print(f"{i:2}. {status_icon} {n['label']}")
        print(f"    attention: {n['attention_score']:.2f} | status: {n['status']}")
        print(f"    dwell: {n['total_dwell_seconds']/60:.0f}min | revisits: {n['revisit_count']}")
        if n.get("description"):
            print(f"    {n['description'][:150]}")
        print()


def cmd_abandoned(args):
    """Show ideas/projects that were dropped."""
    nodes = get_abandoned_nodes(limit=20)

    if not nodes:
        print("No abandoned projects detected.")
        return

    print("\n═══ ABANDONED PROJECTS & IDEAS ═══\n")
    for i, n in enumerate(nodes, 1):
        first = n.get("first_seen", "")[:10]
        last = n.get("last_seen", "")[:10]
        print(f"{i:2}. [{n['node_type']}] {n['label']}")
        print(f"    first seen: {first} | last seen: {last}")
        print(f"    peak attention: {n['attention_score']:.2f}")
        print(f"    total dwell: {n['total_dwell_seconds']/3600:.1f}h")
        if n.get("description"):
            print(f"    {n['description'][:150]}")
        print()


def cmd_context(args):
    """Show what was happening around a given time."""
    time_desc = args.time if args.time else "recently"

    print(f"\n═══ CONTEXT: {time_desc} ═══\n")

    nodes = get_top_nodes(limit=10, min_attention=0.05)
    if nodes:
        print("Active topics:")
        for n in nodes[:5]:
            print(f"  • {n['label']} ({n['node_type']}, attention: {n['attention_score']:.2f})")

    # Also check abandoned to see if anything was recently active
    abandoned = get_abandoned_nodes(limit=5)
    if abandoned:
        print("\nRecently dropped:")
        for n in abandoned[:3]:
            last = n.get("last_seen", "")[:10]
            print(f"  • {n['label']} (last seen: {last})")

    print()


def cmd_recurring(args):
    """Show projects that keep coming back (high revisit, active status)."""
    db = get_db()
    rows = db.execute("""
        SELECT * FROM intent_nodes
        WHERE revisit_count >= 3 AND status IN ('active', 'dormant')
        ORDER BY revisit_count DESC
        LIMIT 20
    """).fetchall()
    db.close()

    if not rows:
        print("No recurring projects detected yet.")
        return

    print("\n═══ RECURRING PROJECTS ═══\n")
    for i, r in enumerate(rows, 1):
        n = dict(r)
        print(f"{i:2}. [{n['node_type']}] {n['label']}")
        print(f"    revisits: {n['revisit_count']} | attention: {n['attention_score']:.2f}")
        print(f"    total dwell: {n['total_dwell_seconds']/3600:.1f}h")
        print(f"    status: {n['status']}")
        print()


def cmd_graph_search(args):
    """Semantic search over the intent graph."""
    nodes = find_similar_nodes(args.query, limit=10, min_similarity=0.4)

    if not nodes:
        print(f"No nodes found matching: {args.query}")
        return

    print(f"\n═══ GRAPH SEARCH: {args.query} ═══\n")
    for i, n in enumerate(nodes, 1):
        sim_bar = "█" * int(n.get("similarity", 0) * 20)
        print(f"{i:2}. [{n['node_type']}] {n['label']}")
        print(f"    match: {sim_bar} {n.get('similarity', 0):.2f}")
        print(f"    attention: {n['attention_score']:.2f} | revisits: {n['revisit_count']}")
        if n.get("description"):
            print(f"    {n['description'][:150]}")
        print()


def cmd_stats(args):
    """Personal analytics overview."""
    db = get_db()

    total_nodes = db.execute("SELECT COUNT(*) as c FROM intent_nodes").fetchone()["c"]
    total_edges = db.execute("SELECT COUNT(*) as c FROM intent_edges").fetchone()["c"]
    active = db.execute("SELECT COUNT(*) as c FROM intent_nodes WHERE status='active'").fetchone()["c"]
    dormant = db.execute("SELECT COUNT(*) as c FROM intent_nodes WHERE status='dormant'").fetchone()["c"]
    abandoned = db.execute("SELECT COUNT(*) as c FROM intent_nodes WHERE status='abandoned'").fetchone()["c"]
    total_events = db.execute("SELECT COUNT(*) as c FROM raw_events").fetchone()["c"]
    total_semantic = db.execute("SELECT COUNT(*) as c FROM semantic_events").fetchone()["c"]

    # Top node types
    types = db.execute("""
        SELECT node_type, COUNT(*) as c, ROUND(AVG(attention_score), 2) as avg_attn
        FROM intent_nodes GROUP BY node_type ORDER BY c DESC
    """).fetchall()

    db.close()

    print("\n═══ OHRIGHT ANALYTICS ═══\n")
    print("Graph:")
    print(f"  Total nodes:       {total_nodes}")
    print(f"  Total edges:       {total_edges}")
    print(f"  Active:            {active}")
    print(f"  Dormant:           {dormant}")
    print(f"  Abandoned:         {abandoned}")
    print()
    print("Events:")
    print(f"  Raw events:        {total_events}")
    print(f"  Semantic events:   {total_semantic}")
    print()
    print("Node types:")
    for t in types:
        print(f"  {t['node_type']:20s} {t['c']:4d} nodes  (avg attention: {t['avg_attn']})")
    print()


def main():
    init_db()

    parser = argparse.ArgumentParser(
        description="OhRight — semantic memory for your digital life",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          ohright obsessions        What am I obsessed with?
          ohright products          What have I researched but not bought?
          ohright abandoned         What did I drop?
          ohright context           What was I doing recently?
          ohright recurring         What keeps coming back?
          ohright graph "monitors"  Search my behavioral graph
          ohright stats             Personal analytics
          ohright decay             Run attention decay
        """)
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("obsessions", help="Top current interests/obsessions")
    subparsers.add_parser("products", help="Products researched but not purchased")
    subparsers.add_parser("abandoned", help="Ideas/projects that were dropped")

    p_ctx = subparsers.add_parser("context", help="What was I doing?")
    p_ctx.add_argument("time", nargs="?", default=None,
                       help="Time reference (e.g., 'lunch', 'morning', '2pm')")

    subparsers.add_parser("recurring", help="Projects that keep coming back")

    p_gs = subparsers.add_parser("graph", help="Search the graph semantically")
    p_gs.add_argument("query", help="Search query")

    subparsers.add_parser("stats", help="Personal analytics overview")
    subparsers.add_parser("decay", help="Run attention decay")

    args = parser.parse_args()

    commands = {
        "obsessions": cmd_obsessions,
        "products": cmd_products,
        "abandoned": cmd_abandoned,
        "context": cmd_context,
        "recurring": cmd_recurring,
        "graph": cmd_graph_search,
        "stats": cmd_stats,
        "decay": lambda a: (decay_attention(), print("Attention decay complete.")),
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
