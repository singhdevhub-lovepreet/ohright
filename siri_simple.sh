#!/bin/bash
# OhRight Siri — simple mode (no dictation needed)
# Usage:
#   bash siri_obsessions.sh   → speaks your current obsessions
#   bash siri_products.sh     → speaks products you're researching
#   bash siri_stats.sh        → speaks graph stats

MODE="${1:-obsessions}"
OHRIGHT_DIR="$HOME/.ohright"

cd "$OHRIGHT_DIR"

RESULT=$(python3 query.py "$MODE" 2>/dev/null)

echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)

if isinstance(data, list):
    if not data:
        print('Nothing tracked yet. Browse more and OhRight will learn your patterns.')
    else:
        top = data[:3]
        items = [d.get('title', '')[:80] for d in top]
        print('Your top topics: ' + '. '.join(items))
elif isinstance(data, dict):
    g = data.get('graph', {})
    e = data.get('events', {})
    t = data.get('types', {})
    top_type = max(t.items(), key=lambda x: x[1]) if t else ('', 0)
    print(f'OhRight tracks {g.get(\"total_nodes\",0)} topics. {g.get(\"active\",0)} active, {g.get(\"abandoned\",0)} abandoned. Most common: {top_type[0]} with {top_type[1]} items.')
else:
    print('OhRight is ready.')
"
