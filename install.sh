#!/bin/bash
# OhRight — one-line installer (alternative to Homebrew)
# curl -fsSL https://raw.githubusercontent.com/singhdevhub-lovepreet/ohright/main/install.sh | bash

set -e

OHRIGHT_HOME="$HOME/.ohright"
REPO="https://github.com/singhdevhub-lovepreet/ohright.git"

echo "🧠 OhRight Installer"
echo "===================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 required. Install from https://python.org or brew install python"
    exit 1
fi
echo "✅ Python $(python3 --version)"

# Clone or update
if [ -d "$OHRIGHT_HOME/.git" ]; then
    echo "📦 Updating OhRight..."
    cd "$OHRIGHT_HOME" && git pull origin main
else
    echo "📦 Installing OhRight..."
    git clone "$REPO" "$OHRIGHT_HOME"
fi

# Install Python deps
echo "📦 Installing dependencies..."
cd "$OHRIGHT_HOME"
pip3 install -r requirements.txt --quiet 2>/dev/null || pip3 install --user -r requirements.txt --quiet

# Install Raycast extension
RAYCAST_DIR="$HOME/Library/Application Support/com.raycast.macos/Script Commands"
if [ -d "$RAYCAST_DIR" ]; then
    echo ""
    echo "📎 Raycast detected. Installing Script Command..."
    cp "$OHRIGHT_HOME/plugins/raycast/ohright-search.sh" "$RAYCAST_DIR/ohright-search.sh"
    echo "   ✅ Installed. Cmd+Space → 'OhRight'"
else
    echo ""
    echo "📎 Raycast not found. Install from https://raycast.com"
    echo "   Then manually copy: plugins/raycast/ohright-search.sh"
    echo "   to ~/Library/Application Support/com.raycast.macos/Script Commands/"
fi

# Setup wizard
echo ""
echo "═══════════════════════════════════════"
echo "  🧠 OhRight Setup"
echo "═══════════════════════════════════════"
echo ""

read -p "OpenAI API key (sk-...): " OPENAI_KEY
if [ -n "$OPENAI_KEY" ]; then
    echo "$OPENAI_KEY" > "$OHRIGHT_HOME/.openai_key"
    chmod 600 "$OHRIGHT_HOME/.openai_key"
    echo "   ✅ OpenAI key saved"
fi

read -p "screenpipe API key (optional, press Enter to skip): " SP_KEY
if [ -n "$SP_KEY" ]; then
    echo "$SP_KEY" > "$OHRIGHT_HOME/.sp_key"
    chmod 600 "$OHRIGHT_HOME/.sp_key"
    echo "   ✅ screenpipe key saved"
fi

echo ""
echo "Checking screenpipe..."
if curl -s http://localhost:3030/health > /dev/null 2>&1; then
    echo "   ✅ screenpipe running"
else
    echo "   ⚠️  screenpipe not running"
    echo "   Start it: npx screenpipe@latest record"
fi

echo ""
echo "═══════════════════════════════════════"
echo "  ✅ OhRight installed!"
echo ""
echo "  Quick commands:"
echo "    ohright obsessions    # Your current interests"
echo "    ohright products      # Products you're researching"
echo "    ohright stats         # Graph analytics"
echo ""
echo "  Raycast:"
echo "    Cmd+Space → 'OhRight' → 'songs I listened to most'"
echo "═══════════════════════════════════════"
