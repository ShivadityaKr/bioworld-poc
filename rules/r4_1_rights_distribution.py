"""
R4.1 — Rights & Distribution Validation

Checks that the Product Category (Item Type Category), Item Type,
and Customer/retailer from Centric are valid under the NLS license.

Logic:
  1. Match Item Type Category → NLS Definitions categories (exact, case-insensitive)
  2. Match Item Type → active lookup items within that category (exact, case-insensitive)
  3. Check retailer restrictions: certain properties are only allowed
     for specific retailers (e.g., Kingdom Hearts → Hot Topic / Box Lunch only)
  4. Check specialty-only flags for certain properties
  If all pass → PASS, else → FAIL

config_data is the parsed NLS dict from nls_parser.
"""
from __future__ import annotations

import pandas as pd
from rules.base_rule import BaseRule
from typing import Set, Dict


class R4_1_RightsDistribution(BaseRule):
    rule_id   = "R4.1"
    rule_name = "Rights & Distribution Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R4.1")
        if not rule_def or rule_def.config_data is None:
            return self._fail("R4.1 NLS config not loaded")

        nls = rule_def.config_data
        licensed_categories: Set[str] = nls.get("licensed_categories", set())
        category_items: Dict[str, Set[str]] = nls.get("category_items", {})
        retailer_restrictions: Dict[str, dict] = nls.get("retailer_restrictions", {})
        specialty_only: Set[str] = nls.get("specialty_only_properties", set())

        item_type_category = str(row.get("Item Type Category", "")).strip()
        item_type = str(row.get("Item Type", "")).strip()
        customer = str(row.get("Customer", "")).strip()
        declared_property = str(row.get("Property", "")).strip()

        if not item_type_category:
            return self._fail("Item Type Category is empty")

        cat_lower = item_type_category.lower()

        if cat_lower not in licensed_categories:
            available = sorted(licensed_categories)
            return self._fail(
                f"Category '{item_type_category}' is not licensed. "
                f"Licensed categories: {', '.join(c.title() for c in available[:10])}"
            )

        if not item_type:
            return self._fail("Item Type is empty; cannot validate against NLS")

        item_lower = item_type.lower()
        allowed_items = category_items.get(cat_lower, set())

        if item_lower not in allowed_items:
            if allowed_items:
                sample = sorted(allowed_items)[:5]
                return self._fail(
                    f"Item Type '{item_type}' not found in licensed items for category "
                    f"'{item_type_category}'. Examples: {', '.join(s.title() for s in sample)}"
                )
            return self._fail(
                f"No licensed item types found for category '{item_type_category}'"
            )

        prop_lower = declared_property.lower()

        if prop_lower in retailer_restrictions:
            restriction = retailer_restrictions[prop_lower]
            allowed_retailers = restriction.get("allowed_retailers", set())
            customer_lower = customer.lower()
            if allowed_retailers and customer_lower not in allowed_retailers:
                return self._fail(
                    f"Property '{declared_property}' is restricted to retailers: "
                    f"{', '.join(r.title() for r in sorted(allowed_retailers))}. "
                    f"Current customer '{customer}' is not allowed."
                )

        if prop_lower in specialty_only:
            specialty_retailers = {"hot topic", "box lunch", "spirit halloween",
                                   "spencers gifts", "disney stores"}
            customer_lower = customer.lower()
            if customer_lower not in specialty_retailers:
                return self._fail(
                    f"Property '{declared_property}' is specialty-only for 2025. "
                    f"Customer '{customer}' is not a specialty retailer."
                )

        return self._pass()
