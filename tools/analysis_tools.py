"""
tools.py — Shared tools used by agents in the War Room system.
Each tool is a plain Python function called programmatically by agents.
"""

import json
import statistics
from typing import Any


# ─────────────────────────────────────────────
# TOOL 1: Metric Aggregation
# ─────────────────────────────────────────────
def aggregate_metrics(metrics: dict, baselines: dict) -> dict:
    """
    Aggregates each time-series metric: computes first value, last value,
    min, max, mean, delta vs baseline, and trend direction.
    """
    results = {}
    for metric_name, series in metrics.items():
        if not series:
            continue
        values = [point["value"] for point in series]
        first_val = values[0]
        last_val = values[-1]
        baseline = baselines.get(metric_name)

        delta_from_baseline = None
        delta_pct = None
        if baseline is not None and baseline != 0:
            delta_from_baseline = round(last_val - baseline, 3)
            delta_pct = round(((last_val - baseline) / baseline) * 100, 2)

        results[metric_name] = {
            "first": first_val,
            "last": last_val,
            "min": min(values),
            "max": max(values),
            "mean": round(statistics.mean(values), 3),
            "baseline": baseline,
            "delta_from_baseline": delta_from_baseline,
            "delta_pct": delta_pct,
            "data_points": len(values),
        }
    return results


# ─────────────────────────────────────────────
# TOOL 2: Anomaly Detection
# ─────────────────────────────────────────────
def detect_anomalies(metrics: dict, thresholds: dict) -> list[dict]:
    """
    Detects threshold breaches and sudden spikes/drops (>20% change day-over-day).
    Returns a list of anomaly dicts with severity labels.
    """
    anomalies = []

    # Threshold breach detection
    breach_checks = {
        "crash_rate_pct": ("max", thresholds.get("crash_rate_pct_max"), "CRITICAL"),
        "api_latency_p95_ms": ("max", thresholds.get("api_latency_p95_ms_max"), "HIGH"),
        "payment_success_rate_pct": ("min", thresholds.get("payment_success_rate_pct_min"), "CRITICAL"),
        "support_ticket_volume": ("max", thresholds.get("support_ticket_volume_max"), "HIGH"),
        "churn_rate_pct": ("max", thresholds.get("churn_rate_pct_max"), "HIGH"),
    }

    for metric_name, (direction, threshold, severity) in breach_checks.items():
        series = metrics.get(metric_name, [])
        if not series or threshold is None:
            continue
        last_val = series[-1]["value"]
        breached = (direction == "max" and last_val > threshold) or \
                   (direction == "min" and last_val < threshold)
        if breached:
            anomalies.append({
                "metric": metric_name,
                "type": "threshold_breach",
                "severity": severity,
                "current_value": last_val,
                "threshold": threshold,
                "direction": direction,
                "message": f"{metric_name} is {last_val} (threshold: {direction} {threshold})"
            })

    # Sudden change detection (>20% day-over-day on final 3 days)
    for metric_name, series in metrics.items():
        if len(series) < 2:
            continue
        values = [p["value"] for p in series]
        # Check last 3 transitions
        for i in range(max(0, len(values) - 4), len(values) - 1):
            prev, curr = values[i], values[i + 1]
            if prev == 0:
                continue
            change_pct = abs((curr - prev) / prev) * 100
            if change_pct > 20:
                anomalies.append({
                    "metric": metric_name,
                    "type": "sudden_change",
                    "severity": "MEDIUM",
                    "day_index": i + 1,
                    "prev_value": prev,
                    "curr_value": curr,
                    "change_pct": round(change_pct, 2),
                    "message": f"{metric_name} changed by {change_pct:.1f}% in one day"
                })

    return anomalies


# ─────────────────────────────────────────────
# TOOL 3: Sentiment Analysis
# ─────────────────────────────────────────────
def analyze_sentiment(feedback: list[dict]) -> dict:
    """
    Performs keyword-based sentiment analysis on user feedback.
    Returns sentiment distribution, top themes, and critical signals.
    """
    positive_keywords = ["love", "great", "amazing", "perfect", "easy", "beautiful",
                         "excellent", "fantastic", "nice", "good", "clean"]
    negative_keywords = ["crash", "broken", "bug", "error", "failed", "issue", "problem",
                         "unusable", "terrible", "lost", "refund", "fix", "revert",
                         "frustrated", "disappear", "freeze", "slow", "fails"]
    critical_keywords = ["refund", "cancel", "switch", "competitor", "revert", "rollback",
                         "uninstall", "lost data", "charged", "double-charged"]

    theme_keywords = {
        "crashes": ["crash", "crashes", "crashing", "crashing"],
        "performance": ["slow", "loading", "lagging", "latency", "speed", "performance"],
        "payment_issues": ["payment", "charged", "refund", "billing", "pay", "upgrade"],
        "data_loss": ["disappeared", "lost", "data", "reset", "gone"],
        "mobile_issues": ["android", "ios", "iphone", "mobile", "app"],
        "positive_ux": ["love", "great", "amazing", "beautiful", "clean", "dark mode"]
    }

    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    theme_counts = {theme: 0 for theme in theme_keywords}
    critical_signals = []
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for entry in feedback:
        text_lower = entry["text"].lower()
        rating = entry.get("rating", 3)
        rating_distribution[rating] = rating_distribution.get(rating, 0) + 1

        # Sentiment by rating
        if rating >= 4:
            sentiment_counts["positive"] += 1
        elif rating <= 2:
            sentiment_counts["negative"] += 1
        else:
            sentiment_counts["neutral"] += 1

        # Theme detection
        for theme, keywords in theme_keywords.items():
            if any(kw in text_lower for kw in keywords):
                theme_counts[theme] += 1

        # Critical signal detection
        if any(kw in text_lower for kw in critical_keywords):
            critical_signals.append({
                "id": entry["id"],
                "date": entry["date"],
                "channel": entry["channel"],
                "text": entry["text"][:120],
                "rating": rating
            })

    total = len(feedback)
    return {
        "total_feedback": total,
        "sentiment_distribution": {
            k: {"count": v, "pct": round(v / total * 100, 1)}
            for k, v in sentiment_counts.items()
        },
        "rating_distribution": rating_distribution,
        "avg_rating": round(sum(e.get("rating", 3) for e in feedback) / total, 2),
        "theme_counts": theme_counts,
        "critical_signals_count": len(critical_signals),
        "critical_signals": critical_signals,
        "top_themes": sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:4]
    }


# ─────────────────────────────────────────────
# TOOL 4: Trend Comparison
# ─────────────────────────────────────────────
def compare_trends(metrics: dict, baselines: dict, window_days: int = 7) -> dict:
    """
    Compares the last N days trend (slope) for each metric against baseline.
    Returns trend direction, magnitude, and status (improving/degrading/stable).
    """
    results = {}
    for metric_name, series in metrics.items():
        if len(series) < 2:
            continue

        values = [p["value"] for p in series]
        recent_values = values[-window_days:]

        # Simple linear trend: last value minus first value of window
        trend_delta = recent_values[-1] - recent_values[0]
        trend_pct = round((trend_delta / recent_values[0]) * 100, 2) if recent_values[0] != 0 else 0

        # For metrics where higher = worse
        higher_is_worse = ["crash_rate_pct", "api_latency_p95_ms", "support_ticket_volume", "churn_rate_pct"]

        if metric_name in higher_is_worse:
            status = "DEGRADING" if trend_delta > 0 else ("IMPROVING" if trend_delta < 0 else "STABLE")
        else:
            status = "IMPROVING" if trend_delta > 0 else ("DEGRADING" if trend_delta < 0 else "STABLE")

        baseline = baselines.get(metric_name)
        vs_baseline = None
        if baseline:
            diff = recent_values[-1] - baseline
            vs_baseline_pct = round((diff / baseline) * 100, 2)
            if metric_name in higher_is_worse:
                vs_baseline = "WORSE" if diff > 0 else ("BETTER" if diff < 0 else "AT_BASELINE")
            else:
                vs_baseline = "BETTER" if diff > 0 else ("WORSE" if diff < 0 else "AT_BASELINE")
        else:
            vs_baseline = "UNKNOWN"
            vs_baseline_pct = None

        results[metric_name] = {
            "trend_status": status,
            "trend_delta": round(trend_delta, 3),
            "trend_pct_change": trend_pct,
            "vs_baseline": vs_baseline,
            "vs_baseline_pct": vs_baseline_pct if baseline else None,
            "window_days": len(recent_values),
        }

    return results
