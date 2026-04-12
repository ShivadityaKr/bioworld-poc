from __future__ import annotations

from engine.config_loader import config_loader, LicensorConfig, RuleDefinition
from typing import Dict, List, Set


def build_context(licensor_id: str) -> dict:
    """
    Builds the context dict passed to every rule.
    Called once per validation run — not once per row.
    Rules never read files; they only access this dict.

    Gate logic: `is_gate` is set at the group level. All sub-rules
    belonging to a gate group are collected in `gate_rule_ids`.
    If *any* sub-rule in a gate group fails for a row, all rules in
    subsequent groups are skipped.
    """
    cfg: LicensorConfig = config_loader.get_config(licensor_id)
    active = cfg.active_rules()

    gate_groups: Set[str] = set(cfg.gate_groups())
    gate_rule_ids: List[str] = [r.id for r in active if r.group in gate_groups]

    return {
        "licensor_id":     licensor_id,
        "display_name":    cfg.display_name,
        "active_rule_ids": [r.id for r in active],
        "gate_rule_ids":   gate_rule_ids,
        "gate_groups":     gate_groups,
        "rules":           {r.id: r for r in cfg.rules},
    }
