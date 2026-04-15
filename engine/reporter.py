from __future__ import annotations

import pandas as pd
from datetime import datetime


def build_output(
    df: pd.DataFrame,
    validation_results: list[dict]
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Returns:
      pass_df   — rows where all rules passed
      error_df  — rows where one or more rules failed
      summary   — aggregate stats + per-style detail for UI rendering
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pass_rows, error_rows = [], []

    for vr in validation_results:
        original = df.loc[vr["row_index"]].to_dict()
        base = {**original, "run_timestamp": timestamp}
        failed = [r for r in vr["results"] if r["status"] == "FAIL"]

        if vr["overall_status"] == "PASS":
            pass_rows.append({
                **base,
                "validation_status": "PASS",
                "submission_status": "Ready for submission",
            })
        else:
            error_rows.append({
                **base,
                "validation_status": "FAIL",
                "submission_status": "Not ready for submission",
                "failed_rules":    ", ".join(r["rule_id"] for r in failed),
                "failure_reasons": " | ".join(
                    f"{r['rule_id']}: {r['reason']}" for r in failed if r["reason"]
                ),
            })

    pass_df  = pd.DataFrame(pass_rows)  if pass_rows  else pd.DataFrame()
    error_df = pd.DataFrame(error_rows) if error_rows else pd.DataFrame()

    total      = len(validation_results)
    pass_count = len(pass_rows)
    fail_count = len(error_rows)
    pass_pct   = round(pass_count / total * 100, 1) if total > 0 else 0.0

    # Per-rule aggregate stats
    rule_stats: dict[str, dict] = {}
    for vr in validation_results:
        for r in vr["results"]:
            rid = r["rule_id"]
            if rid not in rule_stats:
                rule_stats[rid] = {"name": r["rule_name"], "pass": 0, "fail": 0, "skip": 0}
            rule_stats[rid][r["status"].lower()] += 1

    summary = {
        "total":            total,
        "pass_count":       pass_count,
        "fail_count":       fail_count,
        "pass_pct":         pass_pct,
        "timestamp":        timestamp,
        "rule_stats":       rule_stats,
        "per_style":        validation_results,   # full row-level detail for style cards
    }

    return pass_df, error_df, summary
