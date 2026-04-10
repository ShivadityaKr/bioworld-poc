"""
R2 — SKU Suffix Validation
Suffix map comes from context["rules"]["R2"].config_data.
Config file may be multi-sheet; the sheet containing a 'Suffix code' column is used.
"""
from __future__ import annotations

import pandas as pd
from rules.base_rule import BaseRule
from typing import Optional


def _extract_suffix_df(config_data) -> Optional[pd.DataFrame]:
    """Return the DataFrame containing the suffix_code column."""
    if isinstance(config_data, pd.DataFrame):
        return config_data
    if isinstance(config_data, dict):
        for sheet_name, df in config_data.items():
            cols_norm = df.columns.str.strip().str.lower().str.replace(" ", "_")
            if "suffix_code" in cols_norm.tolist():
                return df
    return None


class R2SKUSuffix(BaseRule):
    rule_id   = "R2"
    rule_name = "SKU Suffix Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R2")
        if not rule_def or rule_def.config_data is None:
            return self._fail("R2 config not loaded")

        df = _extract_suffix_df(rule_def.config_data)
        if df is None:
            return self._fail("R2 config has no sheet with a 'Suffix code' column")

        sku = str(row.get("Style #", "")).strip()
        if len(sku) < 3:
            return self._fail(f"Style # '{sku}' too short to extract suffix (needs >= 3 chars)")

        suffix = sku[-3:].upper()
        df = df.copy()
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        match = df[df["suffix_code"].astype(str).str.strip().str.upper() == suffix]
        if match.empty:
            valid = sorted(
                {str(x).strip().upper() for x in df["suffix_code"].dropna().astype(str) if str(x).strip()}
            )
            return self._fail(
                f"Suffix '{suffix}' not in approved list. Valid suffixes: {', '.join(valid)}"
            )
        return self._pass()
