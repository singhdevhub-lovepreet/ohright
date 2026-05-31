# OhRight Distribution Strategy

## User Flow (goal: 3 steps, under 2 minutes)

```
Step 1: brew install ohright            # one command
Step 2: ohright setup                   # guided setup (API keys, screenpipe)
Step 3: Install Raycast extension       # one click from Raycast Store
```

## Layer 1: Homebrew Formula

Users install the CLI via Homebrew:

```bash
brew tap singhdevhub-lovepreet/ohright
brew install ohright
```

This installs:
- All Python scripts to `/usr/local/share/ohright/`
- `ohright` CLI command (symlink to `orchestrator.py`)
- Python dependencies via `requirements.txt`
- The `ohright-setup` guided setup wizard

## Layer 2: Raycast Extension

Published on the Raycast Store. Users search "OhRight" and click Install.

The extension:
- Talks to `~/.ohright/` via `query.py` shell calls
- Rich UI: list items with attention bars, type emojis, detail view
- Actions: Open in Browser, Copy URL, Copy Title
- Setup wizard if OhRight isn't installed
- Commands: Ask, Obsessions, Products, Setup

## Layer 3: Setup Wizard (included in brew install)

```
$ ohright setup

  🧠 OhRight Setup
  ─────────────────
  
  [1/3] OpenAI API key: sk-...     (reads from input)
  [2/3] Starting screenpipe...     (npx screenpipe@latest record)
  [3/3] Testing pipeline...        (runs one cycle)
  
  ✅ Ready! Cmd+Space → "OhRight"
```

## Files to distribute

```
ohright/
├── raycast-extension/           # → Raycast Store (one-click install)
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── ask.ts               # Main search command
│   │   ├── obsessions.ts        # Quick obsessions
│   │   ├── products.ts          # Shopping research
│   │   ├── setup.ts             # Setup wizard
│   │   └── shared.ts            # Shared utilities
│   └── assets/
│       └── icon.png
│
├── Formula/
│   └── ohright.rb               # Homebrew formula
│
├── install.sh                   # One-line curl installer (alt to brew)
│
├── orchestrator.py              # Main daemon
├── query.py                     # JSON API
├── ask.py                       # NL query engine
├── extract.py                   # Semantic extraction
├── graph.py                     # Behavioral graph
├── url_enrich.py                # URL metadata parsing
├── embeddings.py                # Vector embeddings
├── db.py                        # SQLite schema
├── cli.py                       # Terminal interface
├── requirements.txt             # Python deps
│
└── README.md                    # Full docs
```

## Distribution Checklist

- [ ] Create `ohright` Homebrew tap repo
- [ ] Write `ohright.rb` formula
- [ ] Write `ohright-setup` interactive wizard
- [ ] Test `brew install` from scratch
- [ ] Submit Raycast extension to Raycast Store
- [ ] Buy ohright.co domain
- [ ] Create landing page at ohright.co
- [ ] Publish v0.1.0 release on GitHub
