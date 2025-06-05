#!/bin/bash
cd /home/tommy/Dev/Pagget
source .venv/bin/activate
python main.py --sync
exec bash  # Keep terminal open
