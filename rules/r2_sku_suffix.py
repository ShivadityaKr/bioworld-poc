"""
R2 — SKU Suffix Validation
Suffix map comes from context["rules"]["R2"].config_data (DataFrame).
Loaded from sku_suffix_mapping.xlsx. No hardcoded values.
"""
import pandas as pd
from rules.base_rule import BaseRule


class R2SKUSuffix(BaseRule):
    rule_id   = "R2"
    rule_name = "SKU Suffix Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R2")
        if not rule_def or rule_def.config_data is None:
            return self._fail("R2 config (sku_suffix_mapping.xlsx) not loaded")

        sku = str(row.get("Style #", "")).strip()
        if len(sku) < 3:
            return self._fail(f"Style # '{sku}' too short to extract suffix (needs ≥ 3 chars)")

        suffix = sku[-3:].upper()
        df: pd.DataFrame = rule_def.config_data.copy()
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        if "suffix_code" not in df.columns:
            return self._fail(
                "R2 config missing required column 'suffix_code' (check sku_suffix_mapping.xlsx headers)"
            )

        match = df[df["suffix_code"].astype(str).str.strip().str.upper() == suffix]
        if match.empty:
            valid = sorted(
                {str(x).strip().upper() for x in df["suffix_code"].dropna().astype(str) if str(x).strip()}
            )
            return self._fail(
                f"Suffix '{suffix}' not in approved list. Valid suffixes: {', '.join(valid)}"
            )
        return self._pass()
