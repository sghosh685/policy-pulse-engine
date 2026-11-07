#!/usr/bin/env python3
"""
NetZeroX Policy Pulse — Main CLI Runner
The central orchestrator for cross-border regulatory intelligence.

Usage:
    python main.py init         # Initialize database and tables
    python main.py scrape       # Scrape 8 US/Canada regulatory sources
    python main.py analyze      # AI & expert regulatory analysis on new items
    python main.py report       # Generate executive briefing
    python main.py export       # Export database to public/data/updates.json
    python main.py pipeline     # Full pipeline (scrape → analyze → report → export)
    python main.py stats        # Display database statistics
"""

import os
import sys

# Ensure execution from project root
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)

from src import database as db
from src.scraper import run_scrape
from src.analyzer import run_analysis
from src.report_generator import generate_report, export_dashboard_json


def cmd_init():
    """Initialize database and schema."""
    db.init_db()


def cmd_scrape():
    """Scrape regulatory sources."""
    db.init_db()
    run_scrape()


def cmd_analyze():
    """Run regulatory analysis on unanalyzed items."""
    db.init_db()
    run_analysis()


def cmd_report():
    """Generate weekly executive briefing and sync dashboard data."""
    db.init_db()
    generate_report()


def cmd_export():
    """Export database directly to public/data/updates.json."""
    db.init_db()
    export_dashboard_json()


def cmd_pipeline():
    """Run end-to-end intelligence pipeline."""
    print("🚀 Starting NetZeroX Policy Pulse Pipeline...")
    print("=" * 60)
    db.init_db()
    scrape_res = run_scrape()
    analyzed_count = run_analysis()
    report_file = generate_report()
    export_dashboard_json()
    print("=" * 60)
    print("🎉 Pipeline Completed Successfully!")
    print(f"   • Scraped: {scrape_res['total_found']} found ({scrape_res['total_new']} new)")
    print(f"   • Analyzed: {analyzed_count} items")
    print(f"   • Executive Report: {report_file}")
    print(f"   • Dashboard Data: public/data/updates.json")


def cmd_stats():
    """Show database statistics."""
    db.init_db()
    stats = db.get_stats()
    print("\n📊 NetZeroX Policy Pulse — Database Metrics")
    print("=" * 45)
    print(f"  Total Items Tracked:  {stats['total_items']}")
    print(f"  Analyzed:             {stats['analyzed']}")
    print(f"  Unanalyzed:           {stats['unanalyzed']}")
    print(f"  By Country:           {stats['by_country']}")
    print(f"  By Impact Severity:   {stats['by_impact']}")
    print("=" * 45)


COMMANDS = {
    "init": cmd_init,
    "scrape": cmd_scrape,
    "analyze": cmd_analyze,
    "report": cmd_report,
    "export": cmd_export,
    "pipeline": cmd_pipeline,
    "stats": cmd_stats,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("NetZeroX Policy Pulse Engine v1.0.0")
        print("Cross-Border Compliance Insurance for Energy Leaders")
        print("=" * 55)
        print("Usage: python main.py <command>")
        print()
        print("Commands:")
        print("  init       Initialize database & apply migrations")
        print("  scrape     Scrape 8 US/Canada regulatory sources")
        print("  analyze    Run AI & domain intelligence analysis")
        print("  report     Generate weekly executive briefing")
        print("  export     Export database to public/data/updates.json")
        print("  pipeline   Run full pipeline (scrape → analyze → report → export)")
        print("  stats      Display database statistics")
        sys.exit(1)

    command = sys.argv[1]
    COMMANDS[command]()


# WSGI handler for Vercel
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


if __name__ == "__main__":
    main()
