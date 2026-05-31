# OhRight — Never Lose Context Again

A semantic memory layer for your digital life. Understands what you're researching, obsessed with, and likely to buy.

## Stack

```
screenpipe → captures screen 24/7 (localhost:3030)
    ↓
orchestrator.py → polls every 1 min, sends to OpenAI gpt-4o-mini
    ↓
extract.py → classifies into semantic events (songs, products, content)
    ↓
graph.py → builds behavioral graph with attention scoring
    ↓
query.py → JSON API for any integration
    ↓
ask.py → AI-driven natural language query engine
    ↓
Raycast plugin ← "OhRight, songs I listened to most"
```

## Setup

```bash
# 1. Start screenpipe
npx screenpipe@latest record

# 2. Install deps
pip install -r requirements.txt

# 3. Set API keys
echo "your-openai-key" > .openai_key
echo "your-screenpipe-key" > .sp_key

# 4. Start the watcher
python3 orchestrator.py --watch --interval 1

# 5. Query your behavioral graph
python3 ask.py "what was I obsessed with this week"
python3 ask.py "products I researched but never bought"
python3 ask.py "songs I listened to most"
```

## Raycast

Copy `plugins/raycast/ohright-search.sh` to:
```
~/Library/Application Support/com.raycast.macos/Script Commands/
```

Then in Raycast: Cmd+Space → "OhRight" → type any natural language query.

## Architecture

```
~/.ohright/
├── orchestrator.py    # Main loop — polls screenpipe
├── extract.py         # GPT-4o-mini semantic event extraction
├── embeddings.py      # OpenAI + Ollama all-minilm:33m
├── graph.py           # Behavioral graph with attention scoring
├── query.py           # JSON API (obsessions, products, abandoned, search, stats)
├── ask.py             # Natural language → graph query (AI-powered)
├── db.py              # SQLite schema
├── cli.py             # Terminal interface
├── clear.py           # Reset graph
├── raycast_ai.sh      # Raycast wrapper
├── siri_simple.sh     # Siri voice query bridge
└── ohright.db         # Behavioral graph database
```
