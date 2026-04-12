"""
R2.1 — Property-Art Cross Check (mock/placeholder)

Checks that if a Property is declared, the Art Ref # is populated
and has a reasonable format. Full DMC portal cross-check is out of
scope for this phase.
"""
from __future__ import annotations

import re
import pandas as pd
from rules.base_rule import BaseRule


class R2_1_PropertyArt(BaseRule):
    rule_id   = "R2.1"
    rule_name = "Property-Art Cross Check"

    def validate(self, row: pd.Series, context: dict) -> dict:
        prop = str(row.get("Property", "")).strip()
        art_ref = str(row.get("Art Ref #", "")).strip()

        if not prop:
            return self._pass()

        if not art_ref or art_ref.lower() in ("nan", "none", ""):
            return self._fail(
                f"Art Ref # is empty for property '{prop}'"
            )

        if len(art_ref) < 2:
            return self._fail(
                f"Art Ref # '{art_ref}' appears too short to be valid"
            )

        return self._pass()
