"""
main.py — War Room Multi-Agent System (LangGraph)
PurpleMerit Technologies — AI/ML Engineer Assessment

Entry point. Builds the LangGraph pipeline, loads inputs, runs the war room,
and writes the structured JSON output + trace log.

Usage:
    python main.py
    python main.py --output-dir ./output
"""

import json
import os
import sys
import argparse
import time
from pathlib import Path
from dotenv import load_dotenv
# Load env vars (.env file or system environment)
load_dotenv()

# Validate API key early
if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY environment variable not set.")
    sys.exit(1)

from langgraph.graph import StateGraph, END

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.state import WarRoomState
from agents.agents_main import (
    data_analyst_node,
    pm_agent_node,
    marketing_agent_node,
    engineering_agent_node,
    risk_agent_node,
    orchestrator_node,
)

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"


def load_inputs() -> dict:
    """Load all input files from the data directory."""
    print("\n📂  Loading input data...")

    with open(DATA_DIR / "metrics.json") as f:
        dashboard = json.load(f)

    with open(DATA_DIR / "user_feedback.json") as f:
        feedback = json.load(f)

    with open(DATA_DIR / "release_notes.md") as f:
        release_notes = f.read()

    print(f"  ✓  Metrics loaded: {len(dashboard['metrics'])} time-series, 14 days")
    print(f"  ✓  User feedback loaded: {len(feedback)} entries")
    print(f"  ✓  Release notes loaded: {len(release_notes)} chars")

    return {
        "metrics": dashboard["metrics"],
        "baselines": dashboard["baselines"],
        "thresholds": dashboard["thresholds"],
        "user_feedback": feedback,
        "release_notes": release_notes,
        # Initialize optional fields
        "aggregated_metrics": None,
        "anomalies": None,
        "sentiment_report": None,
        "trend_report": None,
        "pm_analysis": None,
        "data_analyst_analysis": None,
        "marketing_analysis": None,
        "risk_analysis": None,
        "engineer_analysis": None,
        "final_decision": None,
        "trace_log": [f"[{time.strftime('%H:%M:%S')}] WAR ROOM INITIATED — SmartDashboard v2.0 Launch Review"],
    }


def build_graph() -> StateGraph:
    """
    Build the LangGraph state graph.

    Agent execution order:
    Data Analyst → PM Agent → Marketing Agent → Engineering Agent → Risk Agent → Orchestrator
    """
    graph = StateGraph(WarRoomState)

    # Register all agent nodes
    graph.add_node("data_analyst",  data_analyst_node)
    graph.add_node("pm_agent",      pm_agent_node)
    graph.add_node("marketing",     marketing_agent_node)
    graph.add_node("engineering",   engineering_agent_node)
    graph.add_node("risk_critic",   risk_agent_node)
    graph.add_node("orchestrator",  orchestrator_node)

    # Sequential pipeline: each agent hands off to the next
    graph.set_entry_point("data_analyst")
    graph.add_edge("data_analyst",  "pm_agent")
    graph.add_edge("pm_agent",      "marketing")
    graph.add_edge("marketing",     "engineering")
    graph.add_edge("engineering",   "risk_critic")
    graph.add_edge("risk_critic",   "orchestrator")
    graph.add_edge("orchestrator",  END)

    return graph.compile()


def save_outputs(state: dict, output_dir: Path) -> tuple[Path, Path]:
    """Save final decision JSON and trace log to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Save structured decision output
    decision_path = output_dir / f"war_room_decision_{timestamp}.json"
    with open(decision_path, "w") as f:
        json.dump(state.get("final_decision", {}), f, indent=2)

    # Save full trace log
    trace_path = output_dir / f"trace_log_{timestamp}.txt"
    with open(trace_path, "w") as f:
        f.write("=== WAR ROOM TRACE LOG ===\n")
        f.write(f"Feature: SmartDashboard v2.0\n")
        f.write(f"Run: {timestamp}\n\n")
        for line in state.get("trace_log", []):
            f.write(line + "\n")
        f.write("\n=== AGENT ANALYSES ===\n\n")
        for agent_key, label in [
            ("data_analyst_analysis", "DATA ANALYST"),
            ("pm_analysis",           "PRODUCT MANAGER"),
            ("marketing_analysis",    "MARKETING / COMMS"),
            ("engineer_analysis",     "ENGINEERING"),
            ("risk_analysis",         "RISK / CRITIC"),
        ]:
            f.write(f"--- {label} ---\n")
            f.write(state.get(agent_key, "N/A") + "\n\n")

    return decision_path, trace_path


def print_summary(decision: dict) -> None:
    """Print a clean summary of the final decision to console."""
    print("\n" + "=" * 65)
    print("  🚨  WAR ROOM FINAL DECISION")
    print("=" * 65)

    d = decision.get("decision", "UNKNOWN")
    emoji = {"Proceed": "✅", "Pause": "⏸️", "Roll Back": "🔴"}.get(d, "❓")
    print(f"\n  {emoji}  DECISION:  {d.upper()}")
    print(f"\n  📋  SUMMARY:  {decision.get('decision_summary', 'N/A')}")
    print(f"\n  🎯  CONFIDENCE: {decision.get('confidence_score', 'N/A')}/100")

    print("\n  KEY DRIVERS:")
    for driver in decision.get("rationale", {}).get("key_drivers", []):
        print(f"    • {driver}")

    print("\n  TOP RISKS:")
    for risk in decision.get("risk_register", [])[:3]:
        sev = risk.get("severity", "")
        icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(sev, "⚪")
        print(f"    {icon} [{sev}] {risk.get('risk', '')}")

    print("\n  IMMEDIATE ACTIONS (0–4h):")
    for action in [a for a in decision.get("action_plan", []) if a.get("timeframe") == "0-4h"]:
        print(f"    → [{action.get('owner', '?')}] {action.get('action', '')}")

    print("\n" + "=" * 65)


def main(output_dir: Path = OUTPUT_DIR):
    print("\n" + "=" * 65)
    print("  🏢  PURPLEMERIT WAR ROOM — Multi-Agent Launch Review")
    print("  📦  Feature: SmartDashboard v2.0")
    print("=" * 65)

    # 1. Load inputs
    initial_state = load_inputs()

    # 2. Build LangGraph pipeline
    print("\n🔧  Building LangGraph agent pipeline...")
    print("  Pipeline: DataAnalyst → PM → Marketing → Engineering → Risk → Orchestrator")
    app = build_graph()

    # 📊 Save LangGraph diagram (Mermaid + optional PNG)
    os.makedirs(output_dir, exist_ok=True)

    g = app.get_graph()

    # Save Mermaid diagram
    mermaid_path = output_dir / "graph.mmd"
    with open(mermaid_path, "w") as f:
        f.write(g.draw_mermaid())

    print(f"📊 Graph diagram saved to: {mermaid_path}")

    # Try saving PNG (optional)
    try:
        png_path = output_dir / "graph.png"
        g.draw_png(str(png_path))
        print(f"🖼️ Graph image saved to: {png_path}")
    except Exception:
        print("⚠️ PNG generation not supported, using Mermaid file")


    # 3. Run the graph
    print("\n🚀  Invoking war room agents...\n")
    start_time = time.time()
    final_state = app.invoke(initial_state)
    elapsed = round(time.time() - start_time, 1)

    print(f"\n⏱️   Total runtime: {elapsed}s")

    # 4. Print summary
    decision = final_state.get("final_decision", {})
    print_summary(decision)

    # 5. Save outputs
    decision_path, trace_path = save_outputs(final_state, output_dir)
    print(f"\n💾  Decision JSON saved:  {decision_path}")
    print(f"📜  Trace log saved:      {trace_path}\n")

    return final_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="War Room Multi-Agent Launch Review System")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Directory to save output files (default: ./output)")
    args = parser.parse_args()
    main(output_dir=args.output_dir)
