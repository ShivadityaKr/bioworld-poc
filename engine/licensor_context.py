from engine.config_loader import config_loader, LicensorConfig, RuleDefinition


def build_context(licensor_id: str) -> dict:
    """
    Builds the context dict passed to every rule.
    Called once per validation run — not once per row.
    Rules never read files; they only access this dict.
    """
    cfg: LicensorConfig = config_loader.get_config(licensor_id)
    active = cfg.active_rules()

    return {
        "licensor_id":     licensor_id,
        "display_name":    cfg.display_name,
        "active_rule_ids": [r.id for r in active],
        "gate_rule_ids":   [r.id for r in active if r.is_gate],
        "rules":           {r.id: r for r in cfg.rules},
    }
