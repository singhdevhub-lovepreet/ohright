#!/bin/bash
source ~/.zshrc
export SCREENPIPE_API_KEY=***.ohright/.sp_key)
cd ~/.ohright
python3 clear.py
exec python3 orchestrator.py --watch --interval 1
