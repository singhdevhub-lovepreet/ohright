"""
OhRight — Semantic Memory Layer for Human Digital Behavior
Database layer: SQLite for intent graph. Embeddings stored as BLOBs.

Vector search is done in Python via numpy cosine similarity (fast enough for
<50K nodes). sqlite-vec can be dropped in later for scale if needed.

Schema:
  - raw_events:    screenpipe events ingested as-is
  - semantic_events: classified events with embeddings
  - intent_nodes:  graph nodes (projects, interests, products, habits)
  - intent_edges:  relationships between nodes
"""

import sqlite3
import json
import os
import numpy as np
from datetime import datetime, timezone

DB_PATH = os.path.expanduser("~/.ohright/ohright.db")


def get_db() -> sqlite3.Connection:
    """Get a connection to the OhRight database."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db():
    """Create all tables if they don't exist."""
    db = get_db()

    # Raw events from screenpipe
    db.execute("""
        CREATE TABLE IF NOT EXISTS raw_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            screenpipe_id TEXT UNIQUE,
            event_type TEXT NOT NULL,
            app_name TEXT,
            window_name TEXT,
            browser_url TEXT,
            text_content TEXT,
            transcription TEXT,
            timestamp TEXT NOT NULL,
            duration_seconds REAL,
            metadata_json TEXT,
            ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Semantic events (classified by LLM)
    db.execute("""
        CREATE TABLE IF NOT EXISTS semantic_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            topic TEXT,
            subcategory TEXT,
            intensity REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            summary TEXT,
            raw_event_ids TEXT,
            embedding BLOB,
            start_time TEXT NOT NULL,
            end_time TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Intent graph nodes
    db.execute("""
        CREATE TABLE IF NOT EXISTS intent_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_type TEXT NOT NULL,
            label TEXT NOT NULL,
            description TEXT,
            attention_score REAL DEFAULT 0.0,
            total_dwell_seconds REAL DEFAULT 0.0,
            revisit_count INTEGER DEFAULT 0,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            embedding BLOB,
            metadata_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Intent graph edges
    db.execute("""
        CREATE TABLE IF NOT EXISTS intent_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_node_id INTEGER NOT NULL,
            to_node_id INTEGER NOT NULL,
            edge_type TEXT NOT NULL,
            weight REAL DEFAULT 0.5,
            evidence_count INTEGER DEFAULT 1,
            metadata_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (from_node_id) REFERENCES intent_nodes(id),
            FOREIGN KEY (to_node_id) REFERENCES intent_nodes(id)
        )
    """)

    db.commit()
    db.close()


def insert_raw_event(event: dict) -> int:
    """Insert a raw screenpipe event. Returns row id or None if duplicate."""
    db = get_db()
    try:
        cursor = db.execute("""
            INSERT OR IGNORE INTO raw_events
                (screenpipe_id, event_type, app_name, window_name, browser_url,
                 text_content, transcription, timestamp, duration_seconds, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get("id"),
            event.get("event_type", "screen"),
            event.get("app_name"),
            event.get("window_name"),
            event.get("browser_url"),
            event.get("text_content"),
            event.get("transcription"),
            event.get("timestamp"),
            event.get("duration_seconds"),
            json.dumps(event.get("metadata", {}))
        ))
        db.commit()
        return cursor.lastrowid
    finally:
        db.close()


def get_unprocessed_events(limit: int = 100) -> list[dict]:
    """Get raw events that haven't been processed into semantic events yet."""
    db = get_db()
    try:
        rows = db.execute("""
            SELECT * FROM raw_events
            WHERE id NOT IN (
                SELECT DISTINCT CAST(json_each.value AS INTEGER)
                FROM semantic_events, json_each(semantic_events.raw_event_ids)
                WHERE json_each.value != ''
            )
            ORDER BY timestamp ASC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_recent_semantic_events(hours: int = 24, limit: int = 50) -> list[dict]:
    """Get recent semantic events for context."""
    db = get_db()
    try:
        rows = db.execute("""
            SELECT * FROM semantic_events
            WHERE created_at > datetime('now', ?)
            ORDER BY intensity DESC, created_at DESC
            LIMIT ?
        """, (f"-{hours} hours", limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_nodes_with_embeddings() -> list[dict]:
    """Get all nodes that have embeddings (for Python-side vector search)."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, label, node_type, description, attention_score, embedding "
            "FROM intent_nodes WHERE embedding IS NOT NULL"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def vector_search(table: str, query_embedding_blob: bytes, limit: int = 10) -> list[dict]:
    """
    Brute-force cosine similarity search over nodes/events with embeddings.
    Fast for <50K rows. Replace with sqlite-vec when scaling.
    
    table: 'intent_nodes' or 'semantic_events'
    """
    query_vec = np.frombuffer(query_embedding_blob, dtype=np.float32)
    
    db = get_db()
    try:
        rows = db.execute(
            f"SELECT * FROM {table} WHERE embedding IS NOT NULL"
        ).fetchall()
        
        results = []
        for row in rows:
            emb_blob = row["embedding"]
            if not emb_blob:
                continue
            emb_vec = np.frombuffer(emb_blob, dtype=np.float32)
            similarity = float(np.dot(query_vec, emb_vec) / 
                             (np.linalg.norm(query_vec) * np.linalg.norm(emb_vec)))
            d = dict(row)
            d["similarity"] = round(similarity, 4)
            results.append(d)
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")

    # Quick smoke test
    db = get_db()
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"Tables: {[t['name'] for t in tables]}")
    db.close()
