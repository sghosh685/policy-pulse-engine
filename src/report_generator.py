"""
NetZeroX Policy Pulse — Report Generator
Builds the weekly executive briefing from the top regulatory updates.
Uses Jinja2 templates to render Markdown reports.
"""

import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from . import database as db


def generate_report(
    days: int = 7,
    max_items: int = 5,
    output_dir: str = "output",
    template_name: str = "weekly_pulse.md",
) -> str:
    """
    Generate the weekly Policy Pulse report.
    Returns the path to the generated file.
    """
    # Get top updates
    updates = db.get_top_updates(days=days, limit=max_items)

    if not updates:
        print("⚠️  No analyzed updates found for the report period.")
        # Generate report with empty data for template testing
        updates = []

    # Get stats
    stats = db.get_stats()

    # Prepare template data
    now = datetime.now()
    report_date = now.strftime("%B %d, %Y")
    week_start = now.strftime("%b %d")

    # Separate by country
    us_updates = [u for u in updates if u["country"] == "US"]
    ca_updates = [u for u in updates if u["country"] == "CA"]

    # Impact emoji mapping
    impact_emoji = {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🟢",
    }

    template_data = {
        "report_date": report_date,
        "week_label": f"Week of {week_start}",
        "updates": updates,
        "us_updates": us_updates,
        "ca_updates": ca_updates,
        "stats": stats,
        "impact_emoji": impact_emoji,
        "total_items": len(updates),
    }

    # Load and render template
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    rendered = template.render(**template_data)

    # Write output
    os.makedirs(output_dir, exist_ok=True)
    filename = f"policy_pulse_{now.strftime('%Y-%m-%d')}.md"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w") as f:
        f.write(rendered)

    # Mark items as sent
    if updates:
        db.mark_as_sent([u["id"] for u in updates])

    print(f"✅ Report generated: {output_path}")
    print(f"   Items included: {len(updates)}")
    return output_path


def generate_flash_alert(update: dict, output_dir: str = "output") -> str:
    """Generate a flash alert for a critical update."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("flash_alert.md")

    rendered = template.render(
        update=update,
        alert_date=datetime.now().strftime("%B %d, %Y %I:%M %p EST"),
    )

    os.makedirs(output_dir, exist_ok=True)
    filename = f"flash_alert_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w") as f:
        f.write(rendered)

    print(f"🚨 Flash Alert generated: {output_path}")
    return output_path


# ── CLI Entry Point ──────────────────────────────────────────
if __name__ == "__main__":
    import os as _os
    _os.chdir(_os.path.dirname(_os.path.dirname(__file__)))
    generate_report()
