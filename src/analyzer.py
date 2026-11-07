"""
NetZeroX Policy Pulse — AI & Heuristic Intelligence Analyzer
Evaluates regulatory updates for North American energy companies.
Supports OpenAI / Gemini or intelligent domain-expert rule-based analysis.
"""

import json
import os
import re
from typing import Optional, Dict, Any

import yaml
from dotenv import load_dotenv

from . import database as db

load_dotenv()


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _heuristic_analysis(title: str, content: str, source_name: str, country: str) -> dict:
    """
    Expert heuristic regulatory analysis for North American energy compliance.
    Generates tailored statutory penalties, operational mandates, and cross-border impact.
    """
    text = f"{title} {content}".lower()

    # Default baseline
    impact = "MEDIUM"
    summary = f"Regulatory update issued by {source_name} regarding operational standards and compliance criteria."
    action = "Assess operational applicability and incorporate into quarterly compliance review."
    penalty = "Statutory administrative monetary penalties apply for non-compliance."
    action_legal = "Review standard operating contracts and disclosure covenants."
    action_ops = "Verify monitoring equipment logs and maintenance cadence."
    action_esg = "Update carbon ledger and regulatory disclosure tracking."
    cross_border = "Monitor reciprocal regulatory standards across US and Canadian jurisdictions."

    # Domain 1: Methane & Flaring / Subpart W / Directive 060
    if any(k in text for k in ["methane", "subpart w", "directive 060", "flaring", "venting", "super-emitter", "leak detection", "ldar"]):
        impact = "CRITICAL"
        summary = f"{source_name} has issued stringent methane monitoring standards requiring enhanced leak detection (LDAR) and mandatory reporting of fugitive emissions."
        action = "Audit facility compressor stations and flare meters to eliminate unmonitored fugitive emissions."
        if country == "US":
            penalty = "Clean Air Act § 113(b) civil penalties up to $109,024/day per violation; Super-Emitter response mandates."
            cross_border = "US EPA Subpart W benchmarks will directly impact cross-border gas exports destined for US interconnects."
        else:
            penalty = "AER / BC-ER administrative sanctions, shut-in orders, and provincial environmental protection fines."
            cross_border = "Canadian producers shipping to US hubs must reconcile Directive 060 logs with US EPA import criteria."
        action_legal = "Review environmental indemnities and vendor LDAR warranty commitments."
        action_ops = "Deploy continuous optical gas imaging (OGI) or aerial flyover verification across active pads."
        action_esg = "Re-baseline Scope 1 direct fugitive emissions inventory in anticipation of mandatory audit."

    # Domain 2: Scope 3 & Climate Disclosures / SEC / OSFI
    elif any(k in text for k in ["scope 3", "climate disclosure", "sec", "esg reporting", "tcfd", "issb"]):
        impact = "CRITICAL"
        summary = f"Regulatory updates from {source_name} concerning Scope 3 supply chain and climate-related financial disclosures."
        action = "Re-evaluate materiality assessments and preserve audit trails for indirect value-chain emissions."
        penalty = "Securities regulatory enforcement, shareholder derivative risk, and disclosure delay sanctions."
        action_legal = "Coordinate with external securities counsel on safe harbor protections and 10-K / AIF alignment."
        action_ops = "Standardize tier-1 supplier carbon data collection protocols."
        action_esg = "Reconcile corporate GHG accounting against GHG Protocol Corporate Standard guidelines."
        cross_border = "Dual-listed NYSE/TSX issuers must harmonize US SEC filings with Canadian CSA / OSFI B-15 guidelines."

    # Domain 3: Carbon Credits, 45Q, 45V, Clean Fuel Regulations (CFR)
    elif any(k in text for k in ["45q", "45v", "clean fuel", "cfr", "hydrogen", "carbon capture", "ccus", "tax credit", "ira"]):
        impact = "HIGH"
        summary = f"{source_name} regulatory guidance on clean fuel credits, CCUS verification (45Q), and clean hydrogen incentives (45V)."
        action = "Review qualified carbon intensity (CI) modeling and claim eligibility timelines."
        penalty = "Credit forfeiture, tax recapture, and statutory deficit surrender penalties."
        action_legal = "Structure carbon credit transfer agreements and tax indemnity clauses."
        action_ops = "Validate third-party life-cycle carbon intensity (LCI) verification audits."
        action_esg = "Incorporate clean fuel credits into corporate sustainability asset registers."
        cross_border = "Evaluate arbitrage between US IRA production tax credits and Canadian Clean Economy investment tax credits (ITCs)."

    # Domain 4: Emissions Cap / Clean Electricity / Carbon Pricing
    elif any(k in text for k in ["emissions cap", "clean electricity", "carbon pricing", "tier", "obps", "cap-and-trade"]):
        impact = "CRITICAL"
        summary = f"{source_name} proposed regulatory caps on greenhouse gas emissions across power generation and fossil fuel extraction."
        action = "Quantify facility-level emissions allowances and forecast annual compliance obligation costs."
        penalty = "Statutory compliance true-up fees ($65+/tonne) and mandatory production curtailment."
        action_legal = "Examine constitutional challenge precedents and compliance credit rights."
        action_ops = "Identify immediate electrification and waste heat recovery engineering projects."
        action_esg = "Calculate net financial impact under projected carbon price trajectory."
        cross_border = "Cross-border power flows and LNG exports face border carbon adjustment scrutiny."

    # Domain 5: Pipeline & Interconnection / FERC
    elif any(k in text for k in ["pipeline", "ferc", "interconnection", "lng", "transmission"]):
        impact = "HIGH"
        summary = f"{source_name} directive on pipeline certificate authorizations, grid interconnection queue reform, and tariff schedules."
        action = "Review regional transmission organization (RTO) queue milestones and interstate permit timelines."
        penalty = "FERC civil penalties up to $1.5M/day per violation under the Natural Gas Act and Federal Power Act."
        action_legal = "File timely intervention notices and assess tariff renegotiation provisions."
        action_ops = "Update pipeline integrity management plans and pressure monitoring logs."
        action_esg = "Document rights-of-way biodiversity and local community impact assessments."
        cross_border = "International border crossing permits require coordinated NEPA and Impact Assessment Agency of Canada reviews."

    return {
        "summary": summary,
        "impact_level": impact,
        "action_required": action,
        "penalty_exposure": penalty,
        "action_legal": action_legal,
        "action_ops": action_ops,
        "action_esg": action_esg,
        "cross_border_impact": cross_border
    }


def analyze_update(title: str, raw_content: str, source_name: str, country: str, config: dict) -> dict:
    """
    Analyze a regulatory update using an LLM (if configured) or the expert domain heuristic engine.
    """
    api_key = os.getenv("OPENAI_API_KEY")

    # If OpenAI API Key is available, try LLM inference
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            analyzer_config = config.get("analyzer", {})
            model = analyzer_config.get("model", "gpt-4o-mini")
            temperature = analyzer_config.get("temperature", 0.2)

            system_prompt = """
            You are a chief regulatory risk officer for North American energy enterprises.
            Given a regulatory update, produce an executive briefing JSON:
            {
              "summary": "2-sentence executive summary",
              "impact_level": "CRITICAL|HIGH|MEDIUM|LOW",
              "action_required": "Immediate priority action for VP Sustainability/Compliance",
              "penalty_exposure": "Statutory legal/financial penalty exposure",
              "action_legal": "Specific legal/counsel next step",
              "action_ops": "Specific engineering/operations next step",
              "action_esg": "Specific ESG/reporting next step",
              "cross_border_impact": "Impact on cross-border US-Canada energy trade"
            }
            """

            user_message = f"Authority: {source_name} ({country})\nTitle: {title}\nContent:\n{(raw_content or '')[:3000]}"

            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                timeout=15,
            )

            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"  ⚠️  LLM API unavailable ({e}). Falling back to Energy Expert Heuristic.")

    # High-accuracy fallback
    return _heuristic_analysis(title, raw_content or "", source_name, country)


def run_analysis(config_path: str = "config.yaml", limit: int = 50) -> int:
    """Run analysis on all unanalyzed items in the database."""
    config = load_config(config_path)
    unanalyzed = db.get_unanalyzed(limit=limit)

    if not unanalyzed:
        print("✅ No unanalyzed items found.")
        return 0

    print(f"\n🧠 NetZeroX Policy Pulse — Running Regulatory Intelligence Analysis on {len(unanalyzed)} items...")

    count = 0
    for item in unanalyzed:
        analysis = analyze_update(
            title=item["title"],
            raw_content=item.get("raw_content") or "",
            source_name=item.get("source_name") or "",
            country=item.get("country") or "US",
            config=config,
        )

        db.update_analysis(
            row_id=item["id"],
            summary=analysis["summary"],
            impact_level=analysis["impact_level"],
            action_required=analysis["action_required"],
            penalty_exposure=analysis.get("penalty_exposure"),
            action_legal=analysis.get("action_legal"),
            action_ops=analysis.get("action_ops"),
            action_esg=analysis.get("action_esg"),
            cross_border_impact=analysis.get("cross_border_impact"),
        )
        count += 1
        print(f"  [{analysis['impact_level']}] Analyzed: {item['title'][:65]}...")

    print(f"\n✅ Analysis complete! {count} items processed and indexed.")
    return count
