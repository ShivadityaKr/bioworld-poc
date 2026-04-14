from __future__ import annotations

import pandas as pd
from rules.rule_registry import RULE_REGISTRY
from typing import List


def run_validation(df: pd.DataFrame, context: dict) -> List[dict]:
    """
    Returns one result dict per input row.

    Every active rule is evaluated for each row. Earlier failures do not
    short-circuit later rules (no gate SKIP behavior).
    """
    active_rule_ids: List[str] = context["active_rule_ids"]
    rules_map = context["rules"]

    results = []

    for idx, row in df.iterrows():
        row_results = []
        overall = "PASS"

        for rule_id in active_rule_ids:
            rule_def = rules_map.get(rule_id)
            rule_name = rule_def.name if rule_def else rule_id

            if rule_id not in RULE_REGISTRY:
                print(f"[Validator] '{rule_id}' active in config but not in RULE_REGISTRY. Skipping.")
                continue

            result = RULE_REGISTRY[rule_id].validate(row, context)
            row_results.append(result)

            if result["status"] == "FAIL":
                overall = "FAIL"

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
