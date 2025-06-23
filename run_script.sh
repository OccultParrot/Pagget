#!/bin/bash
cd /home/tommy/Dev/Pagget || exit
# Pulling newest version
git pull origin main
source .venv/bin/activate
python main.py
exec bash  # Keep terminal open
