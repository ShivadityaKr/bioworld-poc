"""
R5.1 — Packaging Rule Validation

Validates packaging rules based on Pre-check steps:
  1. Correct type of packaging must be linked
  2. Packaging must use same property and art references as the style
  3. Retailer-specific packaging checks (Walmart hangtag, Spencer's bellyband)
  4. Neck Pillows must be sold with coordinating luggage

For fields we can validate from Centric data:
  - Item Type Category == "Packaging" → must have Property and Art Ref #
  - Specific item types have retailer constraints
  - Neck Pillow items must be in Luggage category
"""
from __future__ import annotations

import pandas as pd
from rules.base_rule import BaseRule


RETAILER_PACKAGING_NOTES = {
    "walmart": "Walmart requires specific hangtag packaging",
    "spencers gifts": "Spencer's requires bellyband packaging",
}


class R5_1_Packaging(BaseRule):
    rule_id   = "R5.1"
    rule_name = "Packaging Rule Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        item_type_category = str(row.get("Item Type Category", "")).strip().lower()
        item_type = str(row.get("Item Type", "")).strip().lower()
        customer = str(row.get("Customer", "")).strip()
        customer_lower = customer.lower()
        prop = str(row.get("Property", "")).strip()
        art_ref = str(row.get("Art Ref #", "")).strip()

        if item_type_category == "packaging":
            if not prop:
                return self._fail(
                    "Packaging items must have the same Property as the parent style"
                )
            if not art_ref or art_ref.lower() == "nan":
                return self._fail(
                    "Packaging items must have Art Ref # linked (same as parent style)"
                )

        if "neck pillow" in item_type:
            return self._fail(
                "[REVIEW] Neck Pillows must coordinate and be sold with "
                "coordinating luggage for the Retailer's luggage buyer/department"
            )

        if item_type_category == "packaging" and customer_lower in RETAILER_PACKAGING_NOTES:
            note = RETAILER_PACKAGING_NOTES[customer_lower]
            return self._fail(f"[REVIEW] {note}")

        licensing_status = str(row.get("Licensing Status", "")).strip().lower()
        needs_review = any(kw in licensing_status for kw in (
            "production", "approved", "sample",
        ))

        if needs_review:
            if not prop:
                return self._fail(
                    "Packaging validation requires Property to be populated"
                )

        return self._pass()
