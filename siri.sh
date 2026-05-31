#!/bin/bash
# ============================================================
# OhRight Siri Bridge
# Called by macOS Shortcuts → Siri → this script → OhRight query API
#
# Shortcut setup:
#   1. Open Shortcuts app
#   2. New Shortcut → Add "Run Shell Script" action
#   3. Set input to "Shortcut Input" (dictated text)
#   4. Paste: bash ~/.ohright/siri.sh "$@"
#   5. Add "Speak Text" action with shell output
#   6. Add "Show Notification" action
#   7. Name it "OhRight Query"
#   8. Say: "Hey Siri, OhRight Query"
# ============================================================

QUERY="$1"
OHRIGHT_DIR="$HOME/.ohright"

# If no query, show obsessions
if [ -z "$QUERY" ]; then
    MODE="obsessions"
else
    MODE="search"
fi

# Run query
RESULT=$(cd "$OHRIGHT_DIR" && python3 query.py "$MODE" "$QUERY" 2>/dev/null)

# Parse JSON into human-readable speech
echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)

if isinstance(data, list):
    if not data:
        # Fallback: show obsessions instead
        import subprocess
        r = subprocess.run(['python3', '$HOME/.ohright/query.py', 'obsessions'], 
                          capture_output=True, text=True, cwd='$HOME/.ohright')
        data2 = json.loads(r.stdout)
        if data2:
            tops = [d['title'][:60] for d in data2[:3]]
            print(f'Nothing specific found. Your current top interests are: {\". \".join(tops)}')
        else:
            print('Nothing found yet. Keep using your computer and OhRight will learn.')
    else:
        lines = []
        for i, item in enumerate(data[:3]):
            title = item.get('title', '')
            if i == 0:
                lines.append(f'Top match: {title}')
            else:
                lines.append(f'Also: {title}')
        print('. '.join(lines))
elif isinstance(data, dict):
    # stats or context
    if 'graph' in data:
        g = data['graph']
        e = data.get('events', {})
        print(f'OhRight has {g[\"total_nodes\"]} topics tracked. {g[\"active\"]} active, {g[\"abandoned\"]} abandoned. {e.get(\"semantic\", 0)} semantic events processed.')
    else:
        print('OhRight is running and learning from your activity.')
else:
    print('OhRight is ready.')
"
