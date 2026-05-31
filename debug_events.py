import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_db, get_unprocessed_events

# Check raw events
events = get_unprocessed_events(limit=5)
print(f"Unprocessed events: {len(events)}")
for e in events[:3]:
    print(json.dumps({k: str(v)[:100] for k, v in e.items() if k != 'embedding'}, indent=2))
    print("---")

# Check total events
db = get_db()
total = db.execute("SELECT COUNT(*) as c FROM raw_events").fetchone()["c"]
semantic = db.execute("SELECT COUNT(*) as c FROM semantic_events").fetchone()["c"]
print(f"\nTotal raw events: {total}, Semantic events: {semantic}")
db.close()
