#!/usr/bin/env python3
"""
NetZeroX Policy Pulse — Main CLI Runner
The single entry point for all Policy Pulse operations.

Usage:
    python main.py scrape       # Scrape all sources
    python main.py analyze      # AI-analyze new items
    python main.py report       # Generate weekly report
    python main.py pipeline     # Run full pipeline (scrape → analyze → report)
    python main.py stats        # Show database stats
    python main.py init         # Initialize database
"""

import os
import sys

# Ensure we're running from the project root
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)

from src import database as db
from src.scraper import run_scrape
from src.analyzer import run_analysis
from src.report_generator import generate_report


def cmd_init():
    """Initialize the database."""
    db.init_db()


def cmd_scrape():
    """Run scrapers across all sources."""
    db.init_db()
    result = run_scrape()
    return result


def cmd_analyze():
    """Run AI analysis on unanalyzed items."""
    run_analysis()


def cmd_report():
    """Generate the weekly report."""
    path = generate_report()
    return path


def cmd_pipeline():
    """Run the full pipeline: scrape → analyze → report."""
    print("\n" + "🔄" * 30)
    print("  POLICY PULSE — FULL PIPELINE")
    print("🔄" * 30 + "\n")

    # Step 1: Scrape
    print("\n📡 STEP 1/3: SCRAPING SOURCES...")
    scrape_result = cmd_scrape()

    # Step 2: Analyze
    print("\n🧠 STEP 2/3: AI ANALYSIS...")
    cmd_analyze()

    # Step 3: Report
    print("\n📄 STEP 3/3: GENERATING REPORT...")
    report_path = cmd_report()

    print("\n" + "✅" * 30)
    print("  PIPELINE COMPLETE")
    print(f"  Report: {report_path}")
    print("✅" * 30 + "\n")

    return report_path


def cmd_stats():
    """Show database statistics."""
    db.init_db()
    stats = db.get_stats()
    print("\n📊 Policy Pulse Database Stats")
    print("=" * 40)
    print(f"  Total Items:   {stats['total_items']}")
    print(f"  Analyzed:      {stats['analyzed']}")
    print(f"  Unanalyzed:    {stats['unanalyzed']}")
    print(f"  By Country:    {stats['by_country']}")
    print(f"  By Impact:     {stats['by_impact']}")
    print("=" * 40)


COMMANDS = {
    "init": cmd_init,
    "scrape": cmd_scrape,
    "analyze": cmd_analyze,
    "report": cmd_report,
    "pipeline": cmd_pipeline,
    "stats": cmd_stats,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("NetZeroX Policy Pulse Engine v0.1.0")
        print("=" * 40)
        print("Usage: python main.py <command>")
        print()
        print("Commands:")
        print("  init       Initialize the database")
        print("  scrape     Scrape all regulatory sources")
        print("  analyze    Run AI analysis on new items")
        print("  report     Generate weekly executive briefing")
        print("  pipeline   Run full pipeline (scrape → analyze → report)")
        print("  stats      Show database statistics")
        sys.exit(1)

    command = sys.argv[1]
    COMMANDS[command]()


if __name__ == "__main__":
    main()


def app(environ, start_response):
    """WSGI entry point for serverless hosting."""
    html_path = os.path.join(PROJECT_DIR, "public", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "rb") as f:
            content = f.read()
    else:
        content = b"<h1>NetZeroX Policy Pulse Engine</h1>"
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [content]

handler = app
