"""
OhRight — Intent Graph Management (Layer 3)
Builds and maintains the behavioral graph: nodes, edges, temporal scoring.

Core operations:
  - upsert_node:   create or update a node (project, interest, product, etc.)
  - link_nodes:    create edges between related nodes
  - decay_attention:  time-based attention decay
  - detect_abandonment: find nodes that dropped off
  - query:         search the graph by topic, time, category
"""

import json
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional

import db as ohright_db
from embeddings import embed_single, embedding_to_blob, cosine_similarity, check_ollama_available


def upsert_node(
    node_type: str,
    label: str,
    description: str = "",
    attention_delta: float = 0.1,
    dwell_seconds: float = 0.0,
) -> int:
    """
    Create or update an intent node. If a node with the same label exists,
    boost its attention score and update last_seen.
    """
    db = ohright_db.get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Check if node already exists by label
    existing = db.execute(
        "SELECT id, attention_score, total_dwell_seconds, revisit_count, status FROM intent_nodes WHERE label = ?",
        (label,)
    ).fetchone()

    if existing:
        # Update existing node
        new_score = min(1.0, existing["attention_score"] + attention_delta)
        new_dwell = existing["total_dwell_seconds"] + dwell_seconds
        new_revisits = existing["revisit_count"] + 1
        # Reactivate if dormant/abandoned
        status = "active" if existing["status"] in ("dormant", "abandoned") else existing["status"]

        db.execute("""
            UPDATE intent_nodes
            SET attention_score = ?, total_dwell_seconds = ?, revisit_count = ?,
                last_seen = ?, status = ?, description = COALESCE(NULLIF(?, ''), description),
                updated_at = ?
            WHERE id = ?
        """, (new_score, new_dwell, new_revisits, now, status, description, now, existing["id"]))
        db.commit()

        # Update embedding if description changed (skip if Ollama busy)
        if description:
            try:
                if check_ollama_available():
                    emb = embedding_to_blob(embed_single(f"{node_type}: {label}: {description}"))
                    db.execute("UPDATE intent_nodes SET embedding = ? WHERE id = ?", (emb, existing["id"]))
                    db.commit()
            except Exception:
                pass

        db.close()
        return existing["id"]

    # Create new node
    emb = None
    try:
        if check_ollama_available():
            emb = embedding_to_blob(
                embed_single(f"{node_type}: {label}: {description or label}")
            )
    except Exception:
        pass

    cursor = db.execute("""
        INSERT INTO intent_nodes
            (node_type, label, description, attention_score, total_dwell_seconds,
             revisit_count, first_seen, last_seen, status, embedding, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
    """, (
        node_type, label, description, attention_delta, dwell_seconds,
        1, now, now, emb, "{}"
    ))
    db.commit()
    node_id = cursor.lastrowid

    # (vector search done in Python now — no sqlite-vec virtual tables needed)

    db.close()
    return node_id


def link_nodes(
    from_id: int,
    to_id: int,
    edge_type: str = "related_to",
    weight: float = 0.5,
) -> int:
    """Create or strengthen an edge between two nodes."""
    db = ohright_db.get_db()

    existing = db.execute("""
        SELECT id, weight, evidence_count FROM intent_edges
        WHERE from_node_id = ? AND to_node_id = ? AND edge_type = ?
    """, (from_id, to_id, edge_type)).fetchone()

    if existing:
        new_weight = min(1.0, (existing["weight"] * existing["evidence_count"] + weight) / (existing["evidence_count"] + 1))
        db.execute("""
            UPDATE intent_edges
            SET weight = ?, evidence_count = evidence_count + 1
            WHERE id = ?
        """, (new_weight, existing["id"]))
        db.commit()
        edge_id = existing["id"]
    else:
        cursor = db.execute("""
            INSERT INTO intent_edges (from_node_id, to_node_id, edge_type, weight)
            VALUES (?, ?, ?, ?)
        """, (from_id, to_id, edge_type, weight))
        db.commit()
        edge_id = cursor.lastrowid

    db.close()
    return edge_id


def decay_attention(half_life_hours: float = 72.0):
    """
    Apply exponential time-based decay to all node attention scores.
    Nodes not seen recently lose attention; abandoned ones get flagged.
    """
    db = ohright_db.get_db()
    now = datetime.now(timezone.utc)

    # Find nodes that need decaying
    rows = db.execute(
        "SELECT id, attention_score, last_seen, updated_at FROM intent_nodes WHERE status != 'completed'"
    ).fetchall()

    for row in rows:
        last_seen = datetime.fromisoformat(row["last_seen"].replace("Z", "+00:00"))
        hours_since = (now - last_seen).total_seconds() / 3600

        if hours_since <= 1:
            continue  # too recent to decay

        # Exponential decay
        decay_factor = 0.5 ** (hours_since / half_life_hours)
        new_score = round(row["attention_score"] * decay_factor, 4)

        # Determine status
        if new_score < 0.05:
            status = "abandoned"
        elif new_score < 0.15:
            status = "dormant"
        else:
            status = "active"

        db.execute("""
            UPDATE intent_nodes
            SET attention_score = ?, status = ?, updated_at = ?
            WHERE id = ?
        """, (new_score, status, now.isoformat(), row["id"]))

    db.commit()
    db.close()


def get_top_nodes(
    limit: int = 10,
    node_type: Optional[str] = None,
    min_attention: float = 0.1,
    status: Optional[str] = None
) -> list[dict]:
    """Get top nodes by attention score with optional filters."""
    db = ohright_db.get_db()

    query = "SELECT * FROM intent_nodes WHERE attention_score >= ?"
    params = [min_attention]

    if node_type:
        query += " AND node_type = ?"
        params.append(node_type)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY attention_score DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_abandoned_nodes(limit: int = 20) -> list[dict]:
    """Get nodes that were once high-attention but dropped off."""
    db = ohright_db.get_db()
    rows = db.execute("""
        SELECT * FROM intent_nodes
        WHERE status = 'abandoned'
        ORDER BY attention_score DESC, last_seen DESC
        LIMIT ?
    """, (limit,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_node_with_edges(node_id: int) -> dict:
    """Get a node with all its edges."""
    db = ohright_db.get_db()
    node = db.execute("SELECT * FROM intent_nodes WHERE id = ?", (node_id,)).fetchone()
    if not node:
        db.close()
        return {}

    # Outgoing edges
    outgoing = db.execute("""
        SELECT e.*, n.label as to_label, n.node_type as to_type
        FROM intent_edges e
        JOIN intent_nodes n ON e.to_node_id = n.id
        WHERE e.from_node_id = ?
        ORDER BY e.weight DESC
    """, (node_id,)).fetchall()

    # Incoming edges
    incoming = db.execute("""
        SELECT e.*, n.label as from_label, n.node_type as from_type
        FROM intent_edges e
        JOIN intent_nodes n ON e.from_node_id = n.id
        WHERE e.to_node_id = ?
        ORDER BY e.weight DESC
    """, (node_id,)).fetchall()

    db.close()
    return {
        **dict(node),
        "outgoing_edges": [dict(e) for e in outgoing],
        "incoming_edges": [dict(e) for e in incoming],
    }


def find_similar_nodes(
    text: str,
    limit: int = 10,
    min_similarity: float = 0.6,
) -> list[dict]:
    """Find nodes semantically similar to a query text using Python-side cosine similarity."""
    try:
        query_emb = embedding_to_blob(embed_single(text))
    except Exception:
        return []

    results = ohright_db.vector_search("intent_nodes", query_emb, limit=limit * 2)
    return [r for r in results if r.get("similarity", 0) >= min_similarity][:limit]


if __name__ == "__main__":
    from .db import init_db
    init_db()

    # Quick demo
    n1 = upsert_node("product", "Dell U4025QW Ultrawide", "Productivity monitor research", attention_delta=0.8)
    n2 = upsert_node("interest", "Home Office Setup", "Desk and monitor optimization", attention_delta=0.6)
    link_nodes(n1, n2, "part_of", 0.9)

    print("Top nodes:")
    for n in get_top_nodes():
        print(f"  {n['node_type']}: {n['label']} (attention: {n['attention_score']})")

    print("\nAbandoned:")
    for n in get_abandoned_nodes():
        print(f"  {n['label']} ({n['status']})")
