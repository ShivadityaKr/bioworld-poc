from __future__ import annotations

import pandas as pd
from rules.rule_registry import RULE_REGISTRY


def run_validation(df: pd.DataFrame, context: dict) -> list[dict]:
    """
    Returns one result dict per input row.
    Gate rule failure: remaining rules for that row get status SKIP.
    """
    active_rule_ids = context["active_rule_ids"]
    gate_rule_ids   = context["gate_rule_ids"]
    results = []

    for idx, row in df.iterrows():
        row_results = []
        overall = "PASS"
        gate_failed = False

        for rule_id in active_rule_ids:
            rule_def  = context["rules"].get(rule_id)
            rule_name = rule_def.name if rule_def else rule_id

            if gate_failed:
                row_results.append({
                    "rule_id": rule_id, "rule_name": rule_name,
                    "status": "SKIP", "reason": "Skipped — upstream gate rule failed"
                })
                continue

            if rule_id not in RULE_REGISTRY:
                print(f"[Validator] '{rule_id}' active in config but not in RULE_REGISTRY. Skipping.")
                continue

            result = RULE_REGISTRY[rule_id].validate(row, context)
            row_results.append(result)

            if result["status"] == "FAIL":
                overall = "FAIL"
                if rule_id in gate_rule_ids:
                    gate_failed = True

        results.append({
            "row_index":      idx,
            "Style #":        str(row.get("Style #", "")),
            "Property":       str(row.get("Property", "")),
            "Licensor":       str(row.get("Licensor", "")),
            "Item Type":      str(row.get("Item Type", "")),
            "Customer":       str(row.get("Customer", "")),
            "results":        row_results,
            "overall_status": overall,
        })

    return results
