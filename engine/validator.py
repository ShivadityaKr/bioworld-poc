from __future__ import annotations

import pandas as pd
from rules.rule_registry import RULE_REGISTRY
from typing import List, Set


def run_validation(df: pd.DataFrame, context: dict) -> List[dict]:
    """
    Returns one result dict per input row.

    Gate logic: `is_gate` is at the group level. If any sub-rule in a
    gate group fails, all rules in subsequent groups get status SKIP.
    """
    active_rule_ids: List[str] = context["active_rule_ids"]
    gate_rule_ids: Set[str] = set(context["gate_rule_ids"])
    rules_map = context["rules"]

    gate_groups: Set[str] = context.get("gate_groups", set())

    results = []

    for idx, row in df.iterrows():
        row_results = []
        overall = "PASS"
        gate_failed = False
        failed_gate_group: str = ""

        for rule_id in active_rule_ids:
            rule_def = rules_map.get(rule_id)
            rule_name = rule_def.name if rule_def else rule_id
            rule_group = rule_def.group if rule_def else ""

            if gate_failed and rule_group != failed_gate_group:
                row_results.append({
                    "rule_id": rule_id, "rule_name": rule_name,
                    "status": "SKIP",
                    "reason": "Skipped — upstream gate rule failed",
                })
                continue

            if rule_id not in RULE_REGISTRY:
                print(f"[Validator] '{rule_id}' active in config but not in RULE_REGISTRY. Skipping.")
                continue

            result = RULE_REGISTRY[rule_id].validate(row, context)
            row_results.append(result)

            if result["status"] == "FAIL":
                overall = "FAIL"
                if rule_id in gate_rule_ids and not gate_failed:
                    gate_failed = True
                    failed_gate_group = rule_group

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
