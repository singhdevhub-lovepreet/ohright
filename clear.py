import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_db
db = get_db()
db.execute("PRAGMA foreign_keys=OFF")
db.execute("DELETE FROM raw_events")
db.execute("DELETE FROM semantic_events")
db.execute("DELETE FROM intent_edges")
db.execute("DELETE FROM intent_nodes")
db.execute("DELETE FROM sqlite_sequence")
db.execute("PRAGMA foreign_keys=ON")
db.commit()
db.close()
print("cleared")
