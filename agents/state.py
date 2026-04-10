"""
state.py — Shared LangGraph state definition for the War Room multi-agent system.
"""

from typing import TypedDict, Optional, Any


class WarRoomState(TypedDict):
    # ── Raw Inputs ──────────────────────────────────────────────
    metrics: dict                        # Raw time-series metrics from JSON
    baselines: dict                      # Baseline values per metric
    thresholds: dict                     # Alert thresholds per metric
    user_feedback: list                  # Raw user feedback entries
    release_notes: str                   # Release notes / known issues text

    # ── Tool Outputs (populated by Data Analyst) ─────────────────
    aggregated_metrics: Optional[dict]
    anomalies: Optional[list]
    sentiment_report: Optional[dict]
    trend_report: Optional[dict]

    # ── Agent Analyses ───────────────────────────────────────────
    pm_analysis: Optional[str]           # PM Agent output
    data_analyst_analysis: Optional[str] # Data Analyst Agent output
    marketing_analysis: Optional[str]    # Marketing/Comms Agent output
    risk_analysis: Optional[str]         # Risk/Critic Agent output
    engineer_analysis: Optional[str]     # (extra) Engineering Agent output

    # ── Final Decision ───────────────────────────────────────────
    final_decision: Optional[dict]       # Structured JSON decision output

    # ── Trace Log ────────────────────────────────────────────────
    trace_log: list[str]                 # Append-only log of all agent steps
