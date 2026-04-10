"""
R3 — Property Validation (text-based checks only)

Uses property_hierarchy.xlsx which has three sheets: Disney, Marvel, Lucas.
config_data is a dict of DataFrames: {"Disney": df, "Marvel": df, "Lucas": df}

Checks performed (both text-only, no portal access needed):
  1. Does the declared Property exist in any sheet of the hierarchy?
  2. Is the Property flagged as DO NOT USE?

Out of scope for this phase: Art Ref # cross-check (requires DMC portal).
"""
from __future__ import annotations

import pandas as pd
from rules.base_rule import BaseRule


def _find_column_ci(df: pd.DataFrame, name: str) -> str | None:
    n = name.lower()
    for c in df.columns:
        if str(c).strip().lower() == n:
            return str(c).strip()
    return None


def _find_do_not_use_column(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        cl = str(c).strip().lower().replace("_", " ")
        if cl in ("do not use", "do not use?"):
            return str(c).strip()
    return None


class R3PropertyValidation(BaseRule):
    rule_id   = "R3"
    rule_name = "Property Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R3")
        if not rule_def or rule_def.config_data is None:
            return self._fail("R3 config (property_hierarchy.xlsx) not loaded")

        declared = str(row.get("Property", "")).strip()
        if not declared:
            return self._fail("Property field is empty")

        hierarchy: dict = rule_def.config_data
        found_row = None
        dnu_col: str | None = None
        declared_norm = declared.lower()

        for sheet_name, df_raw in hierarchy.items():
            df = df_raw.copy()
            df.columns = df.columns.astype(str).str.strip()
            prop_col = _find_column_ci(df, "property")
            if prop_col is None:
                return self._fail(
                    f"R3 sheet '{sheet_name}' missing a 'Property' column"
                )
            dnu_col = _find_do_not_use_column(df)
            df["_lv_norm"] = df[prop_col].astype(str).str.strip().str.lower()
            match = df[df["_lv_norm"] == declared_norm]
            if not match.empty:
                found_row = match.iloc[0]
                break

        if found_row is None:
            return self._fail(
                f"Property '{declared}' not found in approved property hierarchy. "
                f"Check spelling or confirm the property is licensed."
            )

        do_not_use_val = None
        if dnu_col and dnu_col in found_row.index:
            do_not_use_val = found_row[dnu_col]

        if do_not_use_val is not None and str(do_not_use_val).strip().lower() not in ("", "nan", "none"):
            return self._fail(
                f"Property '{declared}' is flagged DO NOT USE: {str(do_not_use_val).strip()}"
            )

        return self._pass()
