#!/usr/bin/env python3
"""
OhRight AI Query Engine
Understands natural language and maps it to graph queries via OpenAI.
Usage: python3 ask.py "fetch me songs I listened to most"
"""

import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Read API key from file or env
def get_openai_key():
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        for path in [
            os.path.expanduser("~/.ohright/.openai_key"),
            os.path.expanduser("~/.ohright/.openai_key"),
        ]:
            if os.path.exists(path):
                with open(path) as f:
                    key = f.read().strip()
                break
    if not key:
        # Try from zshrc
        zshrc = os.path.expanduser("~/.zshrc")
        if os.path.exists(zshrc):
            with open(zshrc) as f:
                for line in f:
                    if "OPENAI_API_KEY" in line:
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    return key


def get_graph_context():
    """Get current graph state as context for the LLM."""
    import subprocess
    r = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "query.py"), "stats"],
        capture_output=True, text=True
    )
    try:
        return json.dumps(json.loads(r.stdout))
    except:
        return "{}"


def understand_query(natural_query: str) -> dict:
    """Use OpenAI to map natural language to a graph query."""
    key = get_openai_key()
    
    # Fallback: basic pattern matching if no key
    if not key:
        return fallback_match(natural_query)
    
    from openai import OpenAI
    client = OpenAI(api_key=key)
    
    context = get_graph_context()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "system",
            "content": f"""You are OhRight — a behavioral intelligence system. You map natural language to graph queries.

Available actions and what they do:
- obsessions  → user's current interests, songs, topics, content consumed (most engaged)
- products    → products user researched, purchase intent, things they might buy
- abandoned   → projects/ideas user dropped or stopped working on
- stats       → graph overview and analytics
- recent      → what happened recently
- search      → semantic search with a specific keyword

Current graph state: {context}

Return ONLY valid JSON:
{{"action": "...", "query": "optional search keyword", "message": "friendly one-line intro"}}

Examples:
"songs I listened to most" → {{"action": "obsessions", "message": "Your most played tracks:"}}
"products I forgot to buy" → {{"action": "products", "message": "Products you researched:"}}
"what was I obsessed with" → {{"action": "obsessions", "message": "Your current obsessions:"}}
"show me abandoned projects" → {{"action": "abandoned", "message": "Things you stopped working on:"}}
"my stats" → {{"action": "stats", "message": "Your behavioral graph:"}}
"monitor research" → {{"action": "search", "query": "monitor", "message": "Searching for monitor:"}}"""
        }, {
            "role": "user",
            "content": natural_query
        }],
        temperature=0.1,
        max_tokens=120,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def fallback_match(query: str) -> dict:
    """Basic keyword matching when OpenAI is unavailable."""
    q = query.lower()
    
    if any(w in q for w in ["obsess", "interest", "into", "doing", "song", "music", "listen", "play"]):
        return {"action": "obsessions", "message": "Your current interests:"}
    if any(w in q for w in ["product", "buy", "shopping", "purchas", "missed", "forgot"]):
        return {"action": "products", "message": "Products you researched:"}
    if any(w in q for w in ["abandon", "drop", "unfinished", "stopped"]):
        return {"action": "abandoned", "message": "Projects you dropped:"}
    if any(w in q for w in ["stat", "graph", "summary", "overview"]):
        return {"action": "stats", "message": "Your behavioral graph:"}
    if any(w in q for w in ["recent", "today", "now"]):
        return {"action": "recent", "message": "Recent activity:"}
    
    return {"action": "search", "query": query, "message": f'Searching for "{query}":'}


from typing import Union

def execute_action(action: dict) -> Union[list, dict]:
    """Execute the mapped query against the graph."""
    import subprocess
    
    cmd = action.get("action", "obsessions")
    search_q = action.get("query", "")
    
    if cmd == "search" and search_q:
        r = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "query.py"), "search", search_q],
            capture_output=True, text=True
        )
    else:
        r = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "query.py"), cmd],
            capture_output=True, text=True
        )
    
    try:
        return json.loads(r.stdout)
    except:
        return []


def format_output(data, message: str) -> str:
    """Format results for Raycast display."""
    lines = []
    
    if isinstance(data, list):
        if not data:
            lines.append("Nothing tracked yet. Keep browsing and OhRight will learn.")
        else:
            if message:
                lines.append(message)
                lines.append("")
            for item in data[:8]:
                title = item.get("title", "")[:75]
                sub = item.get("subtitle", "")[:90]
                attn = item.get("attention", 0) or item.get("match", 0)
                bar = "█" * int(attn * 10) + "░" * (10 - int(attn * 10))
                lines.append(f"  {bar}  {title}")
                if sub:
                    lines.append(f"        {sub}")
                # Show URL if available — Raycast auto-detects and makes clickable
                url = item.get("url", "")
                if url:
                    lines.append(f"        🔗 {url}")
                lines.append("")
    elif isinstance(data, dict):
        g = data.get("graph", {})
        e = data.get("events", {})
        t = data.get("types", {})
        if message:
            lines.append(message)
            lines.append("")
        lines.append(f"  Topics tracked:  {g.get('total_nodes', 0)}")
        lines.append(f"  Active:          {g.get('active', 0)}")
        lines.append(f"  Abandoned:       {g.get('abandoned', 0)}")
        lines.append(f"  Events:          {e.get('raw', 0)} raw → {e.get('semantic', 0)} semantic")
        if t:
            top = max(t, key=t.get)
            lines.append(f"  Top category:    {top} ({t[top]})")
        lines.append("")
    else:
        lines.append(str(data))
    
    return "\n".join(lines)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "what am I obsessed with"
    
    action = understand_query(query)
    
    data = execute_action(action)
    
    message = action.get("message", "")
    output = format_output(data, message)
    print(output)
