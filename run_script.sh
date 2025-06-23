#!/bin/bash
echo "Navigating to Pagget directory"
cd /home/tommy/Dev/Pagget || exit
# Pulling newest version
echo "Pulling latest version..."
git pull origin main
echo ""
echo "Running the bot"
source .venv/bin/activate
python main.py
exec bash  # Keep terminal open
