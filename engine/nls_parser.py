"""
Parses NLS (New License Summary) Excel files.

Extracts:
  1. Property-to-suffix mappings from the "New License Summary" sheet
  2. Category/Item Type definitions from the "Definitions" sheet (for Rights validation)
  3. Property-specific retailer restrictions from the "New License Summary" sheet
"""
from __future__ import annotations

import pandas as pd
from typing import Dict, List, Set, Tuple, Optional


def parse_nls(file_path: str) -> dict:
    """
    Returns {
        "suffix_to_properties": {"DSC": ["LILO & STITCH", ...], ...},
        "property_to_suffix":   {"LILO & STITCH": "DSC", ...},
        "all_licensed":         {"lilo & stitch", ...},
        "definitions":          [...],
        "licensed_categories":  {"bags", "apparel", ...},
        "category_items":       {"bags": {"backpack", ...}, ...},
        "specialty_only_properties": {"lilo & stitch", "nightmare before christmas", ...},
        "retailer_restrictions": {
            "kingdom hearts iii": {"allowed_retailers": {"hot topic", "box lunch"}},
        },
    }
    """
    result = _parse_license_sheet(file_path)
    defs = _parse_definitions_sheet(file_path)
    result.update(defs)
    restrictions = _parse_retailer_restrictions(file_path)
    result.update(restrictions)
    return result


def _parse_license_sheet(file_path: str) -> dict:
    df = pd.read_excel(file_path, sheet_name="New License Summary", header=None)

    skip_keywords = {
        "contract", "date:", "licensor:", "print date", "brand",
        "aquisitioner", "confidential", "sell off", "coordinator",
    }

    suffix_to_properties: Dict[str, List[str]] = {}
    property_to_suffix: Dict[str, str] = {}

    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row if str(v).strip() not in ("", "nan", "NaT")]
        if not vals:
            continue

        joined = " ".join(vals).lower()
        if any(kw in joined for kw in skip_keywords):
            continue

        if vals[0] == "License: " or vals[0] == "License:":
            vals = vals[1:]

        j = 0
        while j < len(vals):
            code = vals[j].strip()
            if 2 <= len(code) <= 4 and code.isalpha() and code.isupper():
                if j + 1 < len(vals):
                    prop = vals[j + 1].strip()
                    if not (len(prop) <= 4 and prop.isalpha() and prop.isupper()):
                        if code not in suffix_to_properties:
                            suffix_to_properties[code] = []
                        suffix_to_properties[code].append(prop)
                        property_to_suffix[prop.upper()] = code
                        j += 2
                        continue
            j += 1

    all_licensed: Set[str] = {p.lower() for p in property_to_suffix}

    return {
        "suffix_to_properties": suffix_to_properties,
        "property_to_suffix": property_to_suffix,
        "all_licensed": all_licensed,
    }


def _parse_definitions_sheet(file_path: str) -> dict:
    """Parse the Definitions sheet for Category -> Item Type mappings."""
    try:
        df = pd.read_excel(file_path, sheet_name="Definitions", header=None)
    except Exception:
        return {
            "definitions": [],
            "licensed_categories": set(),
            "category_items": {},
        }

    definitions: List[dict] = []
    licensed_categories: Set[str] = set()
    category_items: Dict[str, Set[str]] = {}

    current_category = ""
    for _, row in df.iterrows():
        cat_val = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        item_val = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""
        code_val = str(row.iloc[3]).strip() if len(row) > 3 and pd.notna(row.iloc[3]) else ""
        active_val = str(row.iloc[5]).strip() if len(row) > 5 and pd.notna(row.iloc[5]) else ""

        if cat_val and cat_val not in ("nan", "Definitions", "Category"):
            current_category = cat_val

        if not item_val or item_val in ("nan", "Lookup Item"):
            continue

        is_active = active_val.lower() in ("true", "yes", "1")
        cat_lower = current_category.lower()
        item_lower = item_val.lower()

        definitions.append({
            "category": current_category,
            "item": item_val,
            "code": code_val,
            "active": is_active,
        })

        if is_active and current_category:
            licensed_categories.add(cat_lower)
            if cat_lower not in category_items:
                category_items[cat_lower] = set()
            category_items[cat_lower].add(item_lower)

    return {
        "definitions": definitions,
        "licensed_categories": licensed_categories,
        "category_items": category_items,
    }


def _parse_retailer_restrictions(file_path: str) -> dict:
    """
    Extract property-specific retailer/distribution restrictions from NLS.

    Known restrictions (from Pre-check steps):
      - KDH (Kingdom Hearts): only allowed for Hot Topic & Box Lunch
      - Lilo & Stitch / NBC: specialty only (2025)
    """
    specialty_only: Set[str] = set()
    retailer_restrictions: Dict[str, dict] = {}

    try:
        df = pd.read_excel(file_path, sheet_name="New License Summary", header=None)
    except Exception:
        return {"specialty_only_properties": specialty_only, "retailer_restrictions": retailer_restrictions}

    for _, row in df.iterrows():
        row_text = " ".join(str(v).strip().lower() for v in row if str(v).strip() not in ("", "nan"))

        if "specialty only" in row_text:
            if "nightmare before christmas" in row_text or "nbc" in row_text:
                specialty_only.add("tim burton's the nightmare before christmas")
            if "lilo" in row_text and "stitch" in row_text:
                specialty_only.add("lilo & stitch")

        if "kingdom hearts" in row_text and ("hot topic" in row_text or "box lunch" in row_text):
            retailer_restrictions["kingdom hearts iii"] = {
                "allowed_retailers": {"hot topic", "box lunch"},
            }
            retailer_restrictions["kingdom hearts franchise"] = {
                "allowed_retailers": {"hot topic", "box lunch"},
            }

    return {
        "specialty_only_properties": specialty_only,
        "retailer_restrictions": retailer_restrictions,
    }


def find_closest_property(declared: str, nls_data: dict) -> Optional[Tuple[str, str]]:
    """
    If `declared` isn't in the NLS, try substring match.
    Returns (matched_property, suffix) or None.
    """
    declared_lower = declared.lower()
    prop_to_suffix = nls_data["property_to_suffix"]

    for nls_prop, suffix in prop_to_suffix.items():
        nls_lower = nls_prop.lower()
        if declared_lower in nls_lower or nls_lower in declared_lower:
            return (nls_prop, suffix)

    return None
