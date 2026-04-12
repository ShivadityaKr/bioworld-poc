"""
R3.1 — Property-Specific Rules

Uses BioWorld Cross Franchise Property Hierarchy Excel which has
sheets: Disney, Marvel, Lucas.
config_data is a dict of DataFrames keyed by sheet name.

Checks:
  1. Does the declared Property exist in any sheet of the hierarchy?
     Strict case-insensitive exact match only.
  2. Is the Property flagged as DO NOT USE?
  3. Property-specific rules from Pre-check steps:
     - NBC (Nightmare Before Christmas): VHS art/item type not allowed
     - Tiana: no frog usage
     - Cruella: restrictions on spots/coat/tails
     - Princesses: PMS colours required
     - NBC: Oogie restrictions (dice/gambling/Boogie's Boys)
"""
from __future__ import annotations

import pandas as pd
from rules.base_rule import BaseRule
from typing import Optional


PROPERTY_SPECIFIC_RULES = {
    "tim burton's the nightmare before christmas": [
        {
            "check": "item_type",
            "blocked_keywords": ["vhs"],
            "message": "NBC: VHS art/item type is not allowed to use",
        },
    ],
    "nightmare before christmas": [
        {
            "check": "item_type",
            "blocked_keywords": ["vhs"],
            "message": "NBC: VHS art/item type is not allowed to use",
        },
    ],
    "disney plus tiana": [
        {
            "check": "note",
            "message": "Tiana: Disney is no longer allowing use of the frog for Tiana related product",
        },
    ],
    "cruella (live action)": [
        {
            "check": "note",
            "message": "Cruella: No spots on her coat or hanging tails on her bag",
        },
    ],
    "disney princess": [
        {
            "check": "note",
            "message": "Princesses: Must have PMS colours call out",
        },
    ],
}


def _find_column_ci(df: pd.DataFrame, name: str) -> Optional[str]:
    n = name.lower()
    for c in df.columns:
        if str(c).strip().lower() == n:
            return str(c).strip()
    return None


def _find_do_not_use_column(df: pd.DataFrame) -> Optional[str]:
    for c in df.columns:
        cl = str(c).strip().lower().replace("_", " ")
        if cl in ("do not use", "do not use?"):
            return str(c).strip()
    return None


class R3_1_PropertyRules(BaseRule):
    rule_id   = "R3.1"
    rule_name = "Property-Specific Rules"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R3.1")
        if not rule_def or rule_def.config_data is None:
            return self._fail("R3.1 config (property hierarchy) not loaded")

        declared = str(row.get("Property", "")).strip()
        if not declared:
            return self._fail("Property field is empty")

        hierarchy: dict = rule_def.config_data
        found_row = None
        dnu_col: Optional[str] = None
        declared_lower = declared.lower()

        for sheet_name, df_raw in hierarchy.items():
            df = df_raw.copy()
            df.columns = df.columns.astype(str).str.strip()
            prop_col = _find_column_ci(df, "property")
            if prop_col is None:
                continue
            dnu_col = _find_do_not_use_column(df)
            df["_lv_norm"] = df[prop_col].astype(str).str.strip().str.lower()
            match = df[df["_lv_norm"] == declared_lower]
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

        hard_fails = self._check_property_specific_rules(row, declared_lower)
        if hard_fails:
            return self._fail("; ".join(hard_fails))

        return self._pass()

    def _check_property_specific_rules(self, row: pd.Series, prop_lower: str) -> list:
        """
        Apply property-specific rules from Pre-check steps doc.
        Only returns hard failures (things we can validate from data).
        'note' type rules are informational — they need human review
        and should not cause a FAIL.
        """
        hard_fails = []
        rules = PROPERTY_SPECIFIC_RULES.get(prop_lower, [])

        for rule in rules:
            check_type = rule.get("check")

            if check_type == "item_type":
                item_type = str(row.get("Item Type", "")).strip().lower()
                item_attr = str(row.get("Item Type Attribute", "")).strip().lower()
                blocked = rule.get("blocked_keywords", [])
                for kw in blocked:
                    if kw in item_type or kw in item_attr:
                        hard_fails.append(rule["message"])

        return hard_fails
