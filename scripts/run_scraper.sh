#!/bin/bash
# NetZeroX Policy Pulse — Cron-friendly scraper entry point
# Add to crontab: 0 6 * * * /path/to/run_scraper.sh
set -e
cd "$(dirname "$0")/.."
python3 main.py scrape
python3 main.py analyze
echo "✅ Scrape + Analysis complete: $(date)"
