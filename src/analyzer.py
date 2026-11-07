"""
NetZeroX Policy Pulse — AI Analyzer
Uses OpenAI GPT-4o-mini to generate executive summaries,
impact ratings, and action items for each regulatory update.
"""

import json
import os
from typing import Optional

import yaml
from dotenv import load_dotenv

from . import database as db

load_dotenv()


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def analyze_update(title: str, raw_content: str, config: dict) -> Optional[dict]:
    """
    Send a regulatory update to OpenAI for analysis.
    Returns: {"summary": str, "impact_level": str, "action_required": str}
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  No OPENAI_API_KEY set. Skipping AI analysis.")
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        analyzer_config = config.get("analyzer", {})
        system_prompt = analyzer_config.get("system_prompt", "Summarize this regulatory update.")
        model = analyzer_config.get("model", "gpt-4o-mini")
        temperature = analyzer_config.get("temperature", 0.3)

        user_message = f"Title: {title}\n\nContent:\n{raw_content[:3000]}"

        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        # Validate expected fields
        return {
            "summary": result.get("summary", "No summary available."),
            "impact_level": result.get("impact_level", "MEDIUM").upper(),
            "action_required": result.get("action_required", "Review and assess applicability."),
        }

    except Exception as e:
        print(f"  ❌ OpenAI error: {e}")
        return None


def analyze_with_fallback(title: str, raw_content: str, keywords_matched: str) -> dict:
    """
    Fallback analysis when no API key is set.
    Uses keyword matching to estimate impact level.
    """
    if keywords_matched:
        keywords = keywords_matched.split(", ")
        critical_kw = {"methane", "ch4", "super-emitter", "subpart w", "scope 3", "emissions cap"}
        if any(kw.lower() in critical_kw for kw in keywords):
            impact = "CRITICAL"
        else:
            impact = "HIGH"
    else:
        impact = "MEDIUM"

    # Generate a basic summary from the title
    summary = f"Regulatory update: {title[:200]}"

    return {
        "summary": summary,
        "impact_level": impact,
        "action_required": "Review this update and assess applicability to your operations.",
    }


def run_analysis(config_path: str = "config.yaml"):
    """Analyze all unanalyzed items in the database."""
    config = load_config(config_path)
    unanalyzed = db.get_unanalyzed(limit=50)

    if not unanalyzed:
        print("✅ No unanalyzed items. Database is up to date.")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    use_ai = bool(api_key)

    print(f"\n🧠 Analyzing {len(unanalyzed)} items...")
    print(f"   Mode: {'AI (OpenAI)' if use_ai else 'Fallback (Keyword)'}")

    for item in unanalyzed:
        title = item["title"]
        raw_content = item.get("raw_content") or title
        keywords_matched = item.get("keywords_matched") or ""

        print(f"  📄 {title[:80]}...")

        if use_ai:
            result = analyze_update(title, raw_content, config)
            if not result:
                result = analyze_with_fallback(title, raw_content, keywords_matched)
        else:
            result = analyze_with_fallback(title, raw_content, keywords_matched)

        db.update_analysis(
            row_id=item["id"],
            summary=result["summary"],
            impact_level=result["impact_level"],
            action_required=result["action_required"],
        )
        print(f"     → {result['impact_level']}")

    print(f"\n✅ Analysis complete. {len(unanalyzed)} items processed.")


# ── CLI Entry Point ──────────────────────────────────────────
if __name__ == "__main__":
    import os as _os
    _os.chdir(_os.path.dirname(_os.path.dirname(__file__)))
    run_analysis()
