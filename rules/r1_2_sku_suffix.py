"""
R1.2 — SKU Suffix Validation

Uses DISNEY PROPERTIES 7.xlsx:
  - Sheet1: Lists Disney properties (col A) and Pixar properties (col C)
  - Sheet2: Maps property categories to suffix codes:
      Pixar Properties         → DSX
      Toddler Properties       → DST
      New Movies               → DSM
      Disney Classics          → DSC
      Disney Channel Properties → DCH
      Standard characters/Princess → DSY

Also cross-references the NLS (via R4.1 config) for per-property suffix
when available, for more precise validation.

Logic:
  1. Check if property is in Pixar list → suffix must be DSX
  2. Check if property is in Disney list → suffix must be one of DST/DSM/DSC/DCH/DSY
  3. If NLS data is available, validate the exact per-property suffix
"""
from __future__ import annotations

import pandas as pd
from rules.base_rule import BaseRule
from typing import Set, Optional, Dict


VALID_DISNEY_SUFFIXES = {"DST", "DSM", "DSC", "DCH", "DSY"}
PIXAR_SUFFIX = "DSX"

SUFFIX_DESCRIPTIONS = {
    "DSX": "Pixar Properties",
    "DST": "Toddler Properties",
    "DSM": "New Movies",
    "DSC": "Disney Classics",
    "DCH": "Disney Channel Properties",
    "DSY": "Standard characters / Princess",
}


def _extract_property_set(df: pd.DataFrame, col_name: str) -> Set[str]:
    """Extract cleaned property names from a column, stripping leading numbers."""
    props: Set[str] = set()
    if col_name not in df.columns:
        return props
    for val in df[col_name].dropna():
        text = str(val).strip().lstrip("0123456789. ").strip()
        if text:
            props.add(text.upper())
    return props


class R1_2_SKUSuffix(BaseRule):
    rule_id   = "R1.2"
    rule_name = "SKU Suffix Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R1.2")
        if not rule_def or rule_def.config_data is None:
            return self._fail("R1.2 config (DISNEY PROPERTIES) not loaded")

        config = rule_def.config_data
        disney_props, pixar_props, suffix_map = self._parse_config(config)

        sku = str(row.get("Style #", "")).strip()
        if len(sku) < 3:
            return self._fail(f"Style # '{sku}' too short to extract suffix")

        declared_property = str(row.get("Property", "")).strip()
        if not declared_property:
            return self._fail("Property field is empty; cannot validate suffix")

        declared_upper = declared_property.upper()
        sku_suffix_3 = sku[-3:].upper()

        nls_suffix = self._get_nls_suffix(declared_upper, context)

        if nls_suffix:
            exp_len = len(nls_suffix)
            actual_suffix = sku[-exp_len:].upper() if len(sku) >= exp_len else sku.upper()
            if actual_suffix != nls_suffix.upper():
                return self._fail(
                    f"SKU suffix '{actual_suffix}' does not match expected "
                    f"'{nls_suffix}' for property '{declared_property}'"
                )
            return self._pass()

        is_pixar = declared_upper in pixar_props
        is_disney = declared_upper in disney_props

        if is_pixar:
            if sku_suffix_3 != PIXAR_SUFFIX:
                return self._fail(
                    f"Pixar property '{declared_property}' requires suffix "
                    f"'{PIXAR_SUFFIX}' but Style # ends with '{sku_suffix_3}'"
                )
            return self._pass()

        if is_disney:
            if sku_suffix_3 not in VALID_DISNEY_SUFFIXES:
                valid_list = ", ".join(sorted(VALID_DISNEY_SUFFIXES))
                return self._fail(
                    f"Disney property '{declared_property}' requires one of "
                    f"[{valid_list}] but Style # ends with '{sku_suffix_3}'"
                )
            return self._pass()

        all_valid = VALID_DISNEY_SUFFIXES | {PIXAR_SUFFIX}
        if sku_suffix_3 in all_valid:
            return self._pass()

        return self._fail(
            f"Property '{declared_property}' not found in Disney/Pixar lists "
            f"and suffix '{sku_suffix_3}' is not a recognized suffix code"
        )

    def _parse_config(self, config) -> tuple:
        """Parse DISNEY PROPERTIES xlsx into property sets and suffix map."""
        disney_props: Set[str] = set()
        pixar_props: Set[str] = set()
        suffix_map: Dict[str, str] = {}

        if isinstance(config, pd.DataFrame):
            disney_props = _extract_property_set(config, "DISNEY PROPERTIES")
            pixar_props = _extract_property_set(config, "PIXAR PROPERTIES")
        elif isinstance(config, dict):
            for sheet_name, df in config.items():
                if sheet_name == "Sheet1":
                    for col in df.columns:
                        col_str = str(col).strip().upper()
                        if "DISNEY" in col_str and "PIXAR" not in col_str:
                            disney_props |= _extract_property_set(df, col)
                        elif "PIXAR" in col_str:
                            pixar_props |= _extract_property_set(df, col)
                elif sheet_name == "Sheet2":
                    for _, r in df.iterrows():
                        prop_cat = str(r.iloc[0]).strip() if pd.notna(r.iloc[0]) else ""
                        code = str(r.iloc[1]).strip() if len(r) > 1 and pd.notna(r.iloc[1]) else ""
                        if prop_cat and code:
                            suffix_map[prop_cat.lower()] = code.strip()

        return disney_props, pixar_props, suffix_map

    def _get_nls_suffix(self, declared_upper: str, context: dict) -> Optional[str]:
        """Try to get per-property suffix from NLS data (loaded for R4.1)."""
        r41_def = context["rules"].get("R4.1")
        if not r41_def or r41_def.config_data is None:
            r12_nls = context["rules"].get("R1.2_nls")
            if r12_nls and r12_nls.config_data:
                return r12_nls.config_data.get("property_to_suffix", {}).get(declared_upper)
            return None
        nls = r41_def.config_data
        return nls.get("property_to_suffix", {}).get(declared_upper)
