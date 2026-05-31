#!/bin/bash

# @raycast.title Search OhRight
# @raycast.author OhRight
# @raycast.description Natural language — "my obsessions", "song", "products", "what am I researching"
# @raycast.schemaVersion 1
# @raycast.mode fullOutput
# @raycast.packageName OhRight
# @raycast.icon 🧠
# @raycast.argument1 {"type": "text", "placeholder": "obsessions, song, product, laptop...", "optional": true}

QUERY="$1"
PYTHON=/usr/bin/python3
DIR="$HOME/.ohright"

# Natural language → command
detect_command() {
    local q
    q=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    
    case "$q" in
        *obsess*|"what am i into"|"my interests"|\
        "what do i like"|"top topics"|"")
            echo "obsessions" ;;

        *product*|"what am i buying"|"what am i shopping"|*purchas*|\
        *shopping*|*buying*)
            echo "products" ;;

        *abandon*|"what did i drop"|*dropped*|*unfinished*)
            echo "abandoned" ;;

        *stat*|"graph"|*analytics*|*summary*)
            echo "stats" ;;

        *recent*|"today"|"last hour"*)
            echo "recent" ;;

        *song*|*music*|*video*|*media*|"what did i listen"|\
        "what did i watch"|*playlist*)
            echo "search"; ARG="song" ;;

        *)  echo "search"; ARG="$1" ;;
    esac
}

MODE=$(detect_command "$QUERY")

cd "$DIR"

if [ "$MODE" = "search" ] && [ -z "$ARG" ]; then
    ARG="$QUERY"
fi

$PYTHON query.py "$MODE" "$ARG" 2>/dev/null | $PYTHON -c "
import sys, json
try:
    data = json.load(sys.stdin)
except:
    print('OhRight is starting up. Try again in a moment.')
    sys.exit(0)

if isinstance(data, list):
    if not data:
        print('Nothing tracked yet. Keep browsing and OhRight will learn.')
    else:
        print()
        for item in data[:6]:
            title = item.get('title', '')[:75]
            sub = item.get('subtitle', '')[:90]
            attn = item.get('attention', 0)
            bar = '█' * int(attn * 10)
            bar2 = '░' * (10 - int(attn * 10))
            print(f'  {bar}{bar2}  {title}')
            if sub:
                print(f'        {sub}')
            print()
else:
    g = data.get('graph', {})
    e = data.get('events', {})
    t = data.get('types', {})
    print()
    print(f'  Total topics:  {g.get(\"total_nodes\", 0)}')
    print(f'  Active:        {g.get(\"active\", 0)}')
    print(f'  Abandoned:     {g.get(\"abandoned\", 0)}')
    print(f'  Raw events:    {e.get(\"raw\", 0)}')
    print(f'  Semantic:      {e.get(\"semantic\", 0)}')
    if t:
        print(f'  Top type:      {max(t, key=t.get)} ({max(t.values())})')
    print()
"
