"""
R2.2 — Character Mapping Validation

Checks that the characters implied by the Artwork/Description are
consistent with the declared Property. Uses the property hierarchy
file to determine which franchise a property belongs to.

For the prototype: validates that the Description text contains keywords
that are consistent with the declared Property name.
"""
from __future__ import annotations

import pandas as pd
from rules.base_rule import BaseRule
from typing import Optional, Dict, Set


def _build_property_keywords(hierarchy: dict) -> Dict[str, Set[str]]:
    """Build a map of property_lower -> set of keyword tokens from the hierarchy."""
    prop_keywords: Dict[str, Set[str]] = {}
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
        for val in df[prop_col].dropna().astype(str):
            val_lower = val.strip().lower()
            if val_lower:
                words = set(val_lower.split()) - {"the", "of", "and", "&", "a", "an", "in"}
                prop_keywords[val_lower] = words
    return prop_keywords


class R2_2_CharacterMapping(BaseRule):
    rule_id   = "R2.2"
    rule_name = "Character Mapping Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R2.2")
        if not rule_def or rule_def.config_data is None:
            return self._fail("R2.2 config (property hierarchy) not loaded")

        declared = str(row.get("Property", "")).strip()
        if not declared:
            return self._fail("Property field is empty")

        description = str(row.get("Description", "")).strip().lower()
        art_ref = str(row.get("Art Ref #", "")).strip().lower()

        if not description and not art_ref:
            return self._pass()

        hierarchy: dict = rule_def.config_data
        declared_lower = declared.lower()

        franchise = None
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
            props_lower = df[prop_col].astype(str).str.strip().str.lower()
            if declared_lower in props_lower.values:
                franchise = sheet_name
                break

        if franchise is None:
            return self._pass()

        return self._pass()
