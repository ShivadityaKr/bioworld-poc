"""
R1 — Mandatory Field Check
Required fields come from context["rules"]["R1"].required_fields (registry YAML).
No hardcoded field names in this file.
"""
import pandas as pd
from rules.base_rule import BaseRule


class R1MandatoryFields(BaseRule):
    rule_id   = "R1"
    rule_name = "Mandatory Field Check"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R1")
        if not rule_def:
            return self._fail("R1 rule definition missing from context")

        missing = []
        for fld in rule_def.required_fields:
            val = row.get(fld["field"], None)
            if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == "":
                missing.append(fld["display"])

        if missing:
            return self._fail(f"Missing required fields: {', '.join(missing)}")
        return self._pass()
