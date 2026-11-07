"""
NetZeroX Policy Pulse — Report Generator & Data Exporter
Builds the weekly executive briefing from the top regulatory updates
and exports structured JSON for the live web dashboard.
"""

import json
import os
from datetime import datetime

import yaml
from jinja2 import Environment, FileSystemLoader

from . import database as db


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def export_dashboard_json(output_path: str = "public/data/updates.json") -> str:
    """
    Export database records, compliance calendar, and statistics to JSON
    for consumption by the web dashboard.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    config = load_config()

    all_updates = db.get_all_updates()
    stats = db.get_stats()
    calendar = config.get("calendar", [])

    # Format updates for UI
    formatted_updates = []
    for u in all_updates:
        formatted_updates.append({
            "id": u["id"],
            "source_id": u["source_id"],
            "source_name": u["source_name"],
            "country": u["country"],
            "title": u["title"],
            "url": u["url"],
            "published_date": u["published_date"],
            "summary": u.get("summary") or "Comprehensive regulatory rule published by governing agency.",
            "impact_level": u.get("impact_level") or "MEDIUM",
            "action_required": u.get("action_required") or "Review standard operating compliance protocols.",
            "penalty_exposure": u.get("penalty_exposure") or "Statutory enforcement sanctions and non-compliance fines.",
            "action_legal": u.get("action_legal") or "Review corporate disclosure requirements and contractual indemnities.",
            "action_ops": u.get("action_ops") or "Ensure monitoring systems and field inspection logs are current.",
            "action_esg": u.get("action_esg") or "Update corporate GHG ledger and sustainability accounting.",
            "cross_border_impact": u.get("cross_border_impact") or "Cross-border regulatory alignment required.",
            "keywords_matched": u.get("keywords_matched") or ""
        })

    payload = {
        "metadata": {
            "project": "NetZeroX Policy Pulse Engine",
            "version": "1.0.0",
            "tagline": "Cross-Border Compliance Insurance for Energy Leaders",
            "last_synced": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "total_items": stats["total_items"],
            "critical_count": stats["by_impact"].get("CRITICAL", 0),
            "high_count": stats["by_impact"].get("HIGH", 0),
            "medium_count": stats["by_impact"].get("MEDIUM", 0),
            "us_count": stats["by_country"].get("US", 0),
            "ca_count": stats["by_country"].get("CA", 0)
        },
        "stats": stats,
        "calendar": calendar,
        "updates": formatted_updates
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"✅ Dashboard data exported successfully to {output_path} ({len(formatted_updates)} items)")
    return output_path


def generate_report(
    days: int = 30,
    max_items: int = 8,
    output_dir: str = "output",
    template_name: str = "weekly_pulse.md",
) -> str:
    """
    Generate the weekly Policy Pulse markdown briefing.
    Returns the path to the generated file.
    """
    updates = db.get_top_updates(days=days, limit=max_items)
    stats = db.get_stats()

    now = datetime.now()
    report_date = now.strftime("%B %d, %Y")
    week_start = f"Week of {now.strftime('%b %d')}"

    us_updates = [u for u in updates if u["country"] == "US"]
    ca_updates = [u for u in updates if u["country"] == "CA"]

    impact_emoji = {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🟢",
    }

    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))

    try:
        template = env.get_template(template_name)
    except Exception:
        # Fallback template if missing
        template_str = """# NetZeroX Policy Pulse — Executive Briefing
**Generated:** {{ report_date }} | **Coverage:** US & Canada Energy Operations

## 📊 High-Level Metrics
- **Total Regulatory Items Monitored:** {{ stats.total_items }}
- **Items Analyzed:** {{ stats.analyzed }}

## 🇺🇸 United States Updates
{% for u in us_updates %}
### {{ loop.index }}. {{ u.title }}
- **Source:** {{ u.source_name }} | **Impact:** {{ u.impact_level }}
- **Summary:** {{ u.summary }}
- **Mandated Action:** {{ u.action_required }}
{% if u.penalty_exposure %}- **Statutory Penalty Risk:** {{ u.penalty_exposure }}{% endif %}
- [Official Rule]({{ u.url }})
{% endfor %}

## 🇨🇦 Canada Updates
{% for u in ca_updates %}
### {{ loop.index }}. {{ u.title }}
- **Source:** {{ u.source_name }} | **Impact:** {{ u.impact_level }}
- **Summary:** {{ u.summary }}
- **Mandated Action:** {{ u.action_required }}
{% if u.penalty_exposure %}- **Statutory Penalty Risk:** {{ u.penalty_exposure }}{% endif %}
- [Official Rule]({{ u.url }})
{% endfor %}
"""
        template = env.from_string(template_str)

    rendered = template.render(
        week_label=week_start,
        report_date=report_date,
        stats=stats,
        total_tracked=stats["total_items"],
        analyzed_count=stats["analyzed"],
        critical_count=stats["by_impact"].get("CRITICAL", 0),
        us_count=stats["by_country"].get("US", 0),
        ca_count=stats["by_country"].get("CA", 0),
        us_updates=us_updates,
        ca_updates=ca_updates,
        impact_emoji=impact_emoji,
    )

    os.makedirs(output_dir, exist_ok=True)
    filename = f"policy_pulse_{now.strftime('%Y-%m-%d')}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"📄 Report generated at: {filepath}")

    # Also export JSON
    export_dashboard_json()

    return filepath
