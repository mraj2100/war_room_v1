# War Room Multi-Agent Launch Review System
### PurpleMerit Technologies — AI/ML Engineer Assessment 1

A multi-agent system built with **LangGraph** that simulates a cross-functional war room during a product launch. The system analyzes a mock dashboard (metrics + user feedback) and produces a structured launch decision: **Proceed / Pause / Roll Back**.

---

## Architecture

```
Input Data (metrics.json, user_feedback.json, release_notes.md)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│              LangGraph State Pipeline                │
│                                                     │
│  [Data Analyst] ──► [PM Agent] ──► [Marketing]      │
│       │                                  │          │
│  (runs 4 tools)                          ▼          │
│                              [Engineering Agent]    │
│                                          │          │
│                                   [Risk/Critic]     │
│                                          │          │
│                                  [Orchestrator] ──► │
└─────────────────────────────────────────────────────┘
        │
        ▼
   war_room_decision_<timestamp>.json
   trace_log_<timestamp>.txt
```

### Agent Roles

| Agent | Responsibility |
|---|---|
| **Data Analyst** | Calls all 4 tools, interprets quantitative metrics, anomalies, trends |
| **Product Manager** | Evaluates success criteria, user impact, go/no-go framing |
| **Marketing/Comms** | Assesses customer sentiment, brand risk, communication actions |
| **Engineering** *(extra)* | Evaluates technical stability, root cause, rollback feasibility |
| **Risk/Critic** | Challenges assumptions, identifies blind spots, worst-case scenarios |
| **Orchestrator** | Synthesizes all agents → final structured JSON decision |

### Tools (called programmatically by Data Analyst Agent)

| Tool | Description |
|---|---|
| `aggregate_metrics()` | Computes first/last/min/max/mean + delta from baseline per metric |
| `detect_anomalies()` | Detects threshold breaches + sudden day-over-day changes (>20%) |
| `analyze_sentiment()` | Keyword-based sentiment scoring, theme extraction, critical signal detection |
| `compare_trends()` | Computes 7-day trend slope and status (IMPROVING/DEGRADING/STABLE) |

---

## Setup Instructions

### 1. Clone / Download the repository

```bash
git clone <your-repo-url>
cd warroom
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API key

```bash
cp .env.example .env
# Edit .env and add your OPENAI API key:
# OPENAI_API_KEY=sk-ant-...
```

Or export directly:
```bash
export OPENAI_API_KEY=sk-your-key-here
```

---

## Running the System

### Basic run

```bash
python main.py
```

### Custom output directory

```bash
python main.py --output-dir ./my_results
```

### Expected output

```
=================================================================
  🏢  PURPLEMERIT WAR ROOM — Multi-Agent Launch Review
  📦  Feature: SmartDashboard v2.0
=================================================================

📂  Loading input data...
  ✓  Metrics loaded: 9 time-series, 14 days
  ✓  User feedback loaded: 35 entries
  ✓  Release notes loaded: 1821 chars

🔧  Building LangGraph agent pipeline...
  Pipeline: DataAnalyst → PM → Marketing → Engineering → Risk → Orchestrator

🚀  Invoking war room agents...

  ▶  DATA ANALYST: Running tool — aggregate_metrics()
  ▶  DATA ANALYST: Running tool — detect_anomalies()
  ▶  DATA ANALYST: Running tool — analyze_sentiment()
  ▶  DATA ANALYST: Running tool — compare_trends()
  ...
  ▶  ORCHESTRATOR: Final decision produced

⏱️   Total runtime: ~45s

=================================================================
  🚨  WAR ROOM FINAL DECISION
=================================================================

  🔴  DECISION:  ROLL BACK
  📋  SUMMARY:  ...
  🎯  CONFIDENCE: 87/100
```

---

## Output Files

Both saved to `./output/` (or your `--output-dir`):

### `war_room_decision_<timestamp>.json`
Structured final decision containing:
- `decision`: Proceed / Pause / Roll Back
- `decision_summary`: One-line rationale
- `rationale`: key drivers, metric references, feedback summary
- `confidence_score`: 0–100
- `confidence_factors`: what increases / decreases confidence
- `risk_register`: top risks with severity + mitigation
- `action_plan`: actions with timeframe (0-4h, 4-24h, 24-48h) and owner
- `communication_plan`: internal and external messaging actions

### `trace_log_<timestamp>.txt`
Full trace containing:
- Timestamped agent steps and tool calls
- Each agent's full analysis narrative
- Pipeline execution order

---

## Traceability

Traces are located in `./output/trace_log_<timestamp>.txt`.

**How to read them:**
- Lines starting with `[HH:MM:SS] AGENT_NAME:` show agent activation and tool calls
- Section headers (`--- DATA ANALYST ---`, etc.) separate each agent's full analysis
- Tool calls are logged before the LLM call for that agent

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ Yes | Your OPENAI API key (`sk-...`) |

---

## Project Structure

```
warroom/
├── main.py                    # Entry point + LangGraph graph definition
├── requirements.txt
├── .env.example
├── README.md
├── agents/
│   ├── state.py               # WarRoomState TypedDict
│   └── agents_main.py              # All 6 agent node functions
├── tools/
│   └── analysis_tools.py      # 4 programmatic tools
├── data/
│   ├── metrics.json           # 14-day time-series (9 metrics)
│   ├── user_feedback.json     # 35 user feedback entries
│   └── release_notes.md       # Feature description + known risks
└── output/
    ├── war_room_decision_<ts>.json
    └── trace_log_<ts>.txt
```

---
