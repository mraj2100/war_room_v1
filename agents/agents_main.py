"""
agents.py — All agent node functions for the War Room LangGraph pipeline.

Each agent:
  1. Receives the shared WarRoomState
  2. Calls the Anthropic API with a role-specific system prompt
  3. Optionally invokes tools (for Data Analyst node)
  4. Returns a state patch dict
"""

import os
import json
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from tools.analysis_tools import (
    aggregate_metrics,
    detect_anomalies,
    analyze_sentiment,
    compare_trends,
)

client = OpenAI()
MODEL = "gpt-4o-mini"


def _call_llm(system: str, user: str, max_tokens: int = 1500) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        max_tokens=max_tokens,
        temperature=0.3
    )

    return response.choices[0].message.content.strip()


def _log(state: dict, message: str) -> list:
    """Return updated trace log with new message."""
    log = list(state.get("trace_log", []))
    log.append(f"[{time.strftime('%H:%M:%S')}] {message}")
    print(f"  ▶  {message}")
    return log


# ─────────────────────────────────────────────────────────────────
# NODE 1: Data Analyst Agent
# Calls all 4 tools, then produces a quantitative analysis narrative
# ─────────────────────────────────────────────────────────────────
def data_analyst_node(state: dict) -> dict:
    log = _log(state, "DATA ANALYST: Running tool — aggregate_metrics()")
    agg = aggregate_metrics(state["metrics"], state["baselines"])

    log = _log({"trace_log": log}, "DATA ANALYST: Running tool — detect_anomalies()")
    anomalies = detect_anomalies(state["metrics"], state["thresholds"])

    log = _log({"trace_log": log}, "DATA ANALYST: Running tool — analyze_sentiment()")
    sentiment = analyze_sentiment(state["user_feedback"])

    log = _log({"trace_log": log}, "DATA ANALYST: Running tool — compare_trends()")
    trends = compare_trends(state["metrics"], state["baselines"])

    # Build compact summary for LLM context
    tool_summary = json.dumps({
        "aggregated_metrics": agg,
        "anomalies": anomalies,
        "sentiment_report": {
            "total": sentiment["total_feedback"],
            "avg_rating": sentiment["avg_rating"],
            "distribution": sentiment["sentiment_distribution"],
            "top_themes": sentiment["top_themes"],
            "critical_signals_count": sentiment["critical_signals_count"],
        },
        "trend_report": trends,
    }, indent=2)

    system = """You are the Data Analyst in a product launch war room.
Your job: interpret quantitative metric data, identify the most critical signals,
spot anomalies, and summarize what the data says objectively.
Be precise. Reference specific metric names and values. Be concise (under 400 words)."""

    user = f"""Here are the tool outputs from your analysis tools:

{tool_summary}

Release context:
{state['release_notes'][:800]}

Provide your data analysis. Cover:
1. Most critical metric issues (with specific values)
2. Key anomalies and threshold breaches
3. Trend direction (improving/degrading)
4. What the data suggests about the health of this launch
"""

    log = _log({"trace_log": log}, "DATA ANALYST: Calling LLM for analysis narrative")
    analysis = _call_llm(system, user)

    return {
        "aggregated_metrics": agg,
        "anomalies": anomalies,
        "sentiment_report": sentiment,
        "trend_report": trends,
        "data_analyst_analysis": analysis,
        "trace_log": _log({"trace_log": log}, "DATA ANALYST: Analysis complete"),
    }


# ─────────────────────────────────────────────────────────────────
# NODE 2: Product Manager Agent
# Frames success criteria, user impact, go/no-go assessment
# ─────────────────────────────────────────────────────────────────
def pm_agent_node(state: dict) -> dict:
    log = _log(state, "PM AGENT: Evaluating success criteria and user impact")

    context = {
        "data_analyst_findings": state.get("data_analyst_analysis", ""),
        "key_metrics_summary": {
            k: v for k, v in (state.get("aggregated_metrics") or {}).items()
            if k in ["activation_conversion_pct", "dau", "d1_retention_pct",
                     "feature_adoption_funnel_pct", "churn_rate_pct"]
        },
        "sentiment": {
            "avg_rating": state.get("sentiment_report", {}).get("avg_rating"),
            "negative_pct": state.get("sentiment_report", {}).get(
                "sentiment_distribution", {}).get("negative", {}).get("pct"),
            "critical_signals_count": state.get("sentiment_report", {}).get("critical_signals_count"),
        },
        "anomaly_count": len(state.get("anomalies") or []),
        "release_notes": state["release_notes"][:600],
    }

    system = """You are the Product Manager in a product launch war room.
Your responsibilities: define what success looks like, assess user impact, and frame
the go/no-go decision from a product and business perspective.
Be direct. Reference data. Limit to 350 words."""

    user = f"""Context from the war room:
{json.dumps(context, indent=2)}

Provide your PM assessment covering:
1. Were launch success criteria met? (activation, retention, adoption)
2. What is the user impact right now?
3. Your initial go/no-go framing and key concerns
4. What would need to change for you to be comfortable proceeding?
"""

    log = _log({"trace_log": log}, "PM AGENT: Calling LLM")
    analysis = _call_llm(system, user)

    return {
        "pm_analysis": analysis,
        "trace_log": _log({"trace_log": log}, "PM AGENT: Analysis complete"),
    }


# ─────────────────────────────────────────────────────────────────
# NODE 3: Marketing / Comms Agent
# Assesses public perception, NPS impact, communication actions
# ─────────────────────────────────────────────────────────────────
def marketing_agent_node(state: dict) -> dict:
    log = _log(state, "MARKETING AGENT: Assessing sentiment and comms posture")

    sentiment = state.get("sentiment_report") or {}
    critical_signals = sentiment.get("critical_signals", [])[:5]

    context = {
        "sentiment_overview": {
            "avg_rating": sentiment.get("avg_rating"),
            "distribution": sentiment.get("sentiment_distribution"),
            "top_themes": sentiment.get("top_themes"),
        },
        "critical_user_signals": critical_signals,
        "support_ticket_trend": {
            k: v for k, v in (state.get("aggregated_metrics") or {}).items()
            if k == "support_ticket_volume"
        },
        "churn_trend": {
            k: v for k, v in (state.get("aggregated_metrics") or {}).items()
            if k == "churn_rate_pct"
        },
        "pm_framing": state.get("pm_analysis", "")[:400],
    }

    system = """You are the Marketing & Communications lead in a product launch war room.
Your job: assess customer perception, brand risk, social media signals, and
recommend communication actions (internal and external).
Be concise and action-oriented. Under 350 words."""

    user = f"""War room context:
{json.dumps(context, indent=2)}

Provide your marketing/comms assessment:
1. Current customer sentiment and brand risk level (Low/Medium/High/Critical)
2. Key themes in negative feedback and what they signal about perception
3. What communication actions are needed in the next 24 hours (internal + external)?
4. What messaging should we avoid right now?
"""

    log = _log({"trace_log": log}, "MARKETING AGENT: Calling LLM")
    analysis = _call_llm(system, user)

    return {
        "marketing_analysis": analysis,
        "trace_log": _log({"trace_log": log}, "MARKETING AGENT: Analysis complete"),
    }


# ─────────────────────────────────────────────────────────────────
# NODE 4: Engineering Agent (Extra Agent)
# Assesses technical health: crashes, latency, payment failures
# ─────────────────────────────────────────────────────────────────
def engineering_agent_node(state: dict) -> dict:
    log = _log(state, "ENGINEERING AGENT: Assessing technical stability")

    agg = state.get("aggregated_metrics") or {}
    anomalies = state.get("anomalies") or []
    critical_anomalies = [a for a in anomalies if a.get("severity") in ("CRITICAL", "HIGH")]

    tech_metrics = {k: v for k, v in agg.items()
                    if k in ["crash_rate_pct", "api_latency_p95_ms",
                             "payment_success_rate_pct", "error_rate_pct"]}

    context = {
        "technical_metrics": tech_metrics,
        "critical_anomalies": critical_anomalies,
        "release_notes_risks": state["release_notes"],
        "data_analyst_findings": state.get("data_analyst_analysis", "")[:400],
    }

    system = """You are the Engineering lead in a product launch war room.
Your job: assess technical stability, identify the root-cause risk areas based on data,
evaluate whether a rollback is technically feasible and advisable, and recommend
immediate engineering actions. Under 350 words. Be technical and specific."""

    user = f"""War room context:
{json.dumps(context, indent=2)}

Provide your engineering assessment:
1. Technical health status (Stable / Unstable / Critical)
2. Most likely root causes based on anomalies and release notes
3. Rollback feasibility (time, risk, data safety)
4. Immediate technical actions needed in next 2-4 hours
"""

    log = _log({"trace_log": log}, "ENGINEERING AGENT: Calling LLM")
    analysis = _call_llm(system, user)

    return {
        "engineer_analysis": analysis,
        "trace_log": _log({"trace_log": log}, "ENGINEERING AGENT: Analysis complete"),
    }


# ─────────────────────────────────────────────────────────────────
# NODE 5: Risk / Critic Agent
# Challenges assumptions, raises blind spots, stress-tests the picture
# ─────────────────────────────────────────────────────────────────
def risk_agent_node(state: dict) -> dict:
    log = _log(state, "RISK/CRITIC AGENT: Challenging assumptions and stress-testing")

    context = {
        "pm_analysis": state.get("pm_analysis", ""),
        "data_analyst_analysis": state.get("data_analyst_analysis", ""),
        "marketing_analysis": state.get("marketing_analysis", ""),
        "engineer_analysis": state.get("engineer_analysis", ""),
        "critical_anomalies": [a for a in (state.get("anomalies") or [])
                                if a.get("severity") == "CRITICAL"],
        "payment_metric": (state.get("aggregated_metrics") or {}).get("payment_success_rate_pct"),
        "crash_metric": (state.get("aggregated_metrics") or {}).get("crash_rate_pct"),
        "churn_metric": (state.get("aggregated_metrics") or {}).get("churn_rate_pct"),
    }

    system = """You are the Risk & Critic analyst in a product launch war room.
Your job: challenge weak assumptions in your colleagues' analyses, highlight risks
they may have underweighted, request missing evidence, and identify what could
get much worse in the next 48 hours. You are NOT here to agree.
Under 400 words. Be sharp and specific."""

    user = f"""Your colleagues have provided these analyses:
{json.dumps(context, indent=2)}

Your critical assessment:
1. What are the 3 biggest risks not adequately addressed above?
2. What assumptions are being made that may not hold?
3. What additional evidence do you need before recommending any decision?
4. What is the worst-case scenario if no action is taken in 24 hours?
5. What is the confidence level in the proposed direction, and what would change it?
"""

    log = _log({"trace_log": log}, "RISK/CRITIC AGENT: Calling LLM")
    analysis = _call_llm(system, user)

    return {
        "risk_analysis": analysis,
        "trace_log": _log({"trace_log": log}, "RISK/CRITIC AGENT: Analysis complete"),
    }


# ─────────────────────────────────────────────────────────────────
# NODE 6: Orchestrator / Coordinator
# Synthesizes all agent views → final structured JSON decision
# ─────────────────────────────────────────────────────────────────
def orchestrator_node(state: dict) -> dict:
    log = _log(state, "ORCHESTRATOR: Synthesizing all agent analyses into final decision")

    full_context = f"""
=== DATA ANALYST ===
{state.get('data_analyst_analysis', 'N/A')}

=== PRODUCT MANAGER ===
{state.get('pm_analysis', 'N/A')}

=== MARKETING / COMMS ===
{state.get('marketing_analysis', 'N/A')}

=== ENGINEERING ===
{state.get('engineer_analysis', 'N/A')}

=== RISK / CRITIC ===
{state.get('risk_analysis', 'N/A')}

=== KEY METRICS SNAPSHOT ===
Crash Rate: {(state.get('aggregated_metrics') or {}).get('crash_rate_pct', {}).get('last', 'N/A')}% (baseline: 0.8%, threshold: 2.0%)
API Latency p95: {(state.get('aggregated_metrics') or {}).get('api_latency_p95_ms', {}).get('last', 'N/A')}ms (baseline: 220ms, threshold: 400ms)
Payment Success: {(state.get('aggregated_metrics') or {}).get('payment_success_rate_pct', {}).get('last', 'N/A')}% (baseline: 98.9%, threshold: 97.0%)
DAU: {(state.get('aggregated_metrics') or {}).get('dau', {}).get('last', 'N/A')} (baseline: 12000)
Churn: {(state.get('aggregated_metrics') or {}).get('churn_rate_pct', {}).get('last', 'N/A')}% (baseline: 1.2%, threshold: 3.0%)
Support Tickets: {(state.get('aggregated_metrics') or {}).get('support_ticket_volume', {}).get('last', 'N/A')} (baseline: 48, threshold: 150)
Avg User Rating: {(state.get('sentiment_report') or {}).get('avg_rating', 'N/A')}
"""

    system = """You are the War Room Coordinator. You have received analyses from 5 specialist agents.
Your job: synthesize their inputs and produce the FINAL structured launch decision.

You MUST respond ONLY with a valid JSON object. No markdown, no prose before or after.
The JSON must follow this exact schema:

{
  "decision": "Proceed" | "Pause" | "Roll Back",
  "decision_summary": "One sentence rationale",
  "rationale": {
    "key_drivers": ["list of 3-5 bullet strings"],
    "metric_references": ["metric: value vs threshold"],
    "feedback_summary": "2-3 sentence summary of user sentiment"
  },
  "confidence_score": 0-100,
  "confidence_factors": {
    "what_increases_confidence": ["list of 2-3 strings"],
    "what_decreases_confidence": ["list of 2-3 strings"]
  },
  "risk_register": [
    {
      "risk": "description",
      "severity": "Critical|High|Medium|Low",
      "mitigation": "action"
    }
  ],
  "action_plan": [
    {
      "timeframe": "0-4h|4-24h|24-48h",
      "action": "description",
      "owner": "role"
    }
  ],
  "communication_plan": {
    "internal": ["list of internal messaging actions"],
    "external": ["list of external/customer-facing actions"]
  }
}"""

    user = f"""Based on all agent analyses and metrics, produce the final war room decision JSON:

{full_context}
"""

    log = _log({"trace_log": log}, "ORCHESTRATOR: Calling LLM for final decision synthesis")
    raw_output = _call_llm(system, user, max_tokens=2000)

    # Parse JSON robustly
    try:
        # Strip any accidental markdown fences
        clean = raw_output.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        final_decision = json.loads(clean.strip())
    except json.JSONDecodeError as e:
        print(f"  ⚠  JSON parse error: {e}. Storing raw output.")
        final_decision = {"raw_output": raw_output, "parse_error": str(e)}

    return {
        "final_decision": final_decision,
        "trace_log": _log({"trace_log": log}, "ORCHESTRATOR: Final decision produced"),
    }
