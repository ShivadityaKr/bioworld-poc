"""
Loads all licensor config at startup. Called once via st.cache_resource.
All validation-time access is in-memory dict lookup only.
"""
from __future__ import annotations

import yaml
import pandas as pd
from pathlib import Path
from dataclasses import dataclass


@dataclass
class RuleDefinition:
    id: str
    name: str
    enabled: bool
    is_gate: bool
    config_file: str | None
    required_fields: list[dict]   # only populated for R1
    config_data: dict | None      # loaded data — dict of DataFrames for multi-sheet files,
                                  # single DataFrame for single-sheet files, or None


@dataclass
class LicensorConfig:
    licensor_id: str
    display_name: str
    config_path: Path
    rules: list[RuleDefinition]

    def active_rules(self) -> list[RuleDefinition]:
        return [r for r in self.rules if r.enabled]

    def get_rule(self, rule_id: str) -> RuleDefinition | None:
        return next((r for r in self.rules if r.id == rule_id), None)


class ConfigLoader:
    def __init__(self, registry_path: str = "config/licensor_registry.yml"):
        self._registry_path = registry_path
        self._configs: dict[str, LicensorConfig] = {}
        self._loaded = False

    def load_all(self) -> None:
        with open(self._registry_path) as f:
            registry = yaml.safe_load(f)

        for licensor_id, meta in registry["licensors"].items():
            if not meta.get("active", False):
                continue
            config_path = Path(meta["config_path"])
            rules = self._load_rules(meta.get("rules", []), config_path)
            self._configs[licensor_id] = LicensorConfig(
                licensor_id=licensor_id,
                display_name=meta["display_name"],
                config_path=config_path,
                rules=rules,
            )

        self._loaded = True
        print(f"[ConfigLoader] Loaded: {list(self._configs.keys())}")

    def get_config(self, licensor_id: str) -> LicensorConfig:
        if not self._loaded:
            raise RuntimeError("ConfigLoader.load_all() must be called first.")
        key = licensor_id.lower().strip()
        if key not in self._configs:
            raise ValueError(f"No config for '{key}'. Available: {list(self._configs.keys())}")
        return self._configs[key]

    def available_licensors(self) -> list[tuple[str, str]]:
        """Returns [(licensor_id, display_name)] for the UI dropdown."""
        return [(k, v.display_name) for k, v in self._configs.items()]

    def _load_rules(self, rules_meta: list[dict], config_path: Path) -> list[RuleDefinition]:
        loaded = []
        for rm in rules_meta:
            config_data = None
            cf = rm.get("config_file")

            if cf:
                full_path = config_path / cf
                if not full_path.exists():
                    print(f"[ConfigLoader] Warning: '{full_path}' not found. "
                          f"Rule {rm['id']} auto-disabled.")
                    rm["enabled"] = False
                else:
                    xl = pd.ExcelFile(full_path)
                    if len(xl.sheet_names) == 1:
                        # Single-sheet file → load as DataFrame directly
                        config_data = pd.read_excel(full_path)
                    else:
                        # Multi-sheet file → load as dict of DataFrames keyed by sheet name
                        config_data = {
                            sheet: pd.read_excel(full_path, sheet_name=sheet)
                            for sheet in xl.sheet_names
                        }

            loaded.append(RuleDefinition(
                id=rm["id"],
                name=rm["name"],
                enabled=rm.get("enabled", False),
                is_gate=rm.get("is_gate", False),
                config_file=cf,
                required_fields=rm.get("required_fields", []),
                config_data=config_data,
            ))
        return loaded


config_loader = ConfigLoader()
