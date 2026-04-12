"""
R5.2 — TM Validation (placeholder — disabled by default)

Placeholder for future Trademark validation rules.
Returns SKIP when evaluated (rule should normally be disabled in config).
"""
from __future__ import annotations

import pandas as pd
from rules.base_rule import BaseRule


class R5_2_TMValidation(BaseRule):
    rule_id   = "R5.2"
    rule_name = "TM Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "status": "SKIP",
            "reason": "Rule disabled — TM validation not yet implemented",
        }
