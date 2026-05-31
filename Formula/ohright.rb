class Ohright < Formula
  desc "OhRight — Never lose context again. Semantic memory layer for macOS."
  homepage "https://github.com/singhdevhub-lovepreet/ohright"
  url "https://github.com/singhdevhub-lovepreet/ohright/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "PLACEHOLDER"
  license "MIT"
  version "0.1.0"

  depends_on "python@3.11"

  resource "openai" do
    url "https://files.pythonhosted.org/packages/source/o/openai/openai-1.55.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/source/r/requests/requests-2.32.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    # Install Python package
    venv = virtualenv_create(libexec, "python3.11")

    # Install all Python files
    (libexec/"ohright").install Dir["*.py"]
    (libexec/"ohright").install "requirements.txt"

    # Install resources
    venv.pip_install resource("openai")
    venv.pip_install resource("requests")

    # Install remaining requirements
    venv.pip_install "-r", libexec/"ohright/requirements.txt"

    # Create CLI wrapper
    (bin/"ohright").write <<~EOS
      #!/bin/bash
      exec #{libexec}/bin/python3 #{libexec}/ohright/cli.py "$@"
    EOS

    # Create setup command
    (bin/"ohright-setup").write <<~EOS
      #!/bin/bash
      echo "🧠 OhRight Setup"
      echo "───────────────"
      echo ""
      
      OHRIGHT_HOME="$HOME/.ohright"
      mkdir -p "$OHRIGHT_HOME"
      
      # Symlink scripts to ~/.ohright/
      for f in #{libexec}/ohright/*.py #{libexec}/ohright/*.sh; do
        ln -sf "$f" "$OHRIGHT_HOME/$(basename $f)" 2>/dev/null
      done
      
      # API keys
      echo "[1/3] OpenAI API key"
      read -s -p "Paste your OpenAI key: " OPENAI_KEY
      echo "$OPENAI_KEY" > "$OHRIGHT_HOME/.openai_key"
      chmod 600 "$OHRIGHT_HOME/.openai_key"
      echo " ✅"
      
      echo "[2/3] screenpipe setup"
      if ! curl -s http://localhost:3030/health > /dev/null 2>&1; then
        echo "Starting screenpipe..."
        npx screenpipe@latest record &
        sleep 15
        echo " ✅"
      else
        echo "screenpipe already running ✅"
      fi
      
      echo "[3/3] Testing pipeline..."
      sleep 5
      python3 "$OHRIGHT_HOME/orchestrator.py" 2>&1 | head -5
      
      echo ""
      echo "✅ OhRight is ready!"
      echo "   Raycast → install 'OhRight' extension from Store"
      echo "   Terminal: ohright obsessions"
    EOS
  end

  def caveats
    <<~EOS
      🧠 OhRight installed!
      
      Quick start:
        ohright-setup              # Guided setup (API keys + screenpipe)
        ohright obsessions         # View your current interests
        ohright products           # View products you're researching
      
      Raycast:
        Install the OhRight extension from Raycast Store for natural language queries.
      
      Dependencies:
        screenpipe must be running: npx screenpipe@latest record
        API keys: ~/.ohright/.openai_key and ~/.ohright/.sp_key
    EOS
  end

  test do
    system "#{bin}/ohright", "--help"
  end
end
