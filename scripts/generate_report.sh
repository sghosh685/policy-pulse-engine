#!/bin/bash
# NetZeroX Policy Pulse — Generate the weekly report
# Run every Friday at 7:30 AM: 30 7 * * 5 /path/to/generate_report.sh
set -e
cd "$(dirname "$0")/.."
python3 main.py pipeline
echo "📄 Weekly report generated: $(date)"
