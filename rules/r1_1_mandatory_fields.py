"""
R1.1 — Mandatory Data Validation

Logic (per Module list.xlsx + Overall Data Mapping):
  Check all required fields are present (NOT NULL / NOT BLANK).

Required fields come from context["rules"]["R1.1"].required_fields.
"""
import pandas as pd
from rules.base_rule import BaseRule


class R1_1_MandatoryFields(BaseRule):
    rule_id   = "R1.1"
    rule_name = "Mandatory Data Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R1.1")
        if not rule_def:
            return self._fail("R1.1 rule definition missing from context")

        missing = []
        for fld in rule_def.required_fields:
            val = row.get(fld["field"], None)
            if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == "":
                missing.append(fld["display"])

        if missing:
            return self._fail(f"Missing required fields: {', '.join(missing)}")
        return self._pass()
