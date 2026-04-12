"""
R3.2 — Property Mixing Validation

Checks that a style does not mix properties from different franchises.

Logic:
  - Identify which franchise (Disney, Marvel, Lucas) the declared
    Property belongs to using the property hierarchy.
  - Strict case-insensitive exact match only.
  - If property not found in any franchise → FAIL.
"""
from __future__ import annotations

import pandas as pd
from rules.base_rule import BaseRule
from typing import Optional


def _property_franchise(declared: str, hierarchy: dict) -> Optional[str]:
    """Return the sheet name (franchise) a property belongs to. Exact match only."""
    declared_lower = declared.lower()

    for sheet_name, df_raw in hierarchy.items():
        df = df_raw.copy()
        df.columns = df.columns.astype(str).str.strip()
        prop_col = None
        for c in df.columns:
            if str(c).strip().lower() == "property":
                prop_col = str(c).strip()
                break
        if not prop_col:
            continue
        props = df[prop_col].astype(str).str.strip().str.lower()
        if declared_lower in props.values:
            return sheet_name

    return None


class R3_2_PropertyMixing(BaseRule):
    rule_id   = "R3.2"
    rule_name = "Property Mixing Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        r31_def = context["rules"].get("R3.1")
        if not r31_def or r31_def.config_data is None:
            return self._pass()

        declared = str(row.get("Property", "")).strip()
        if not declared:
            return self._pass()

        hierarchy: dict = r31_def.config_data
        franchise = _property_franchise(declared, hierarchy)

        if franchise is None:
            return self._fail(
                f"Property '{declared}' not found in any franchise (Disney/Marvel/Lucas)"
            )

        return self._pass()
