#!/bin/bash

# @raycast.title OhRight
# @raycast.author OhRight
# @raycast.description Natural language — "songs I listened to", "products I forgot", "what was I obsessed with"
# @raycast.schemaVersion 1
# @raycast.mode fullOutput
# @raycast.packageName OhRight
# @raycast.icon 🧠
# @raycast.argument1 {"type": "text", "placeholder": "Ask anything about your digital life...", "optional": true}

/usr/bin/python3 ~/.ohright/ask.py "$1"
