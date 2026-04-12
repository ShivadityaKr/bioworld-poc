"""
Loads all licensor config at startup.
Supports grouped rules with sub_rules from the YAML registry.
"""
from __future__ import annotations

import yaml
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from engine.nls_parser import parse_nls


@dataclass
class RuleDefinition:
    id: str
    name: str
    enabled: bool
    is_gate: bool
    group: str
    group_name: str
    config_file: Optional[str]
    config_type: Optional[str]
    required_fields: List[dict]
    config_data: Any = None


@dataclass
class LicensorConfig:
    licensor_id: str
    display_name: str
    config_path: Path
    rules: List[RuleDefinition]

    def active_rules(self) -> List[RuleDefinition]:
        return [r for r in self.rules if r.enabled]

    def get_rule(self, rule_id: str) -> Optional[RuleDefinition]:
        return next((r for r in self.rules if r.id == rule_id), None)

    def gate_groups(self) -> List[str]:
        """Return group IDs that are gates."""
        seen: Dict[str, bool] = {}
        for r in self.rules:
            if r.group not in seen:
                seen[r.group] = r.is_gate
        return [g for g, is_g in seen.items() if is_g]


class ConfigLoader:
    def __init__(self, registry_path: str = "config/licensor_registry.yml"):
        self._registry_path = registry_path
        self._configs: Dict[str, LicensorConfig] = {}
        self._loaded = False
        self._nls_cache: Dict[str, dict] = {}

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

    def available_licensors(self) -> List[Tuple[str, str]]:
        return [(k, v.display_name) for k, v in self._configs.items()]

    # ------------------------------------------------------------------

    def _load_nls(self, full_path: Path) -> dict:
        key = str(full_path)
        if key not in self._nls_cache:
            self._nls_cache[key] = parse_nls(str(full_path))
        return self._nls_cache[key]

    def _load_config_data(self, cf: str, config_type: Optional[str],
                          config_path: Path) -> Any:
        """Load config_data from an Excel file, using NLS parser when needed."""
        full_path = config_path / cf
        if not full_path.exists():
            return None

        if config_type == "nls":
            return self._load_nls(full_path)

        xl = pd.ExcelFile(full_path)
        if len(xl.sheet_names) == 1:
            return pd.read_excel(full_path)
        return {
            sheet: pd.read_excel(full_path, sheet_name=sheet)
            for sheet in xl.sheet_names
        }

    def _load_rules(self, rules_meta: List[dict], config_path: Path) -> List[RuleDefinition]:
        loaded: List[RuleDefinition] = []

        for group in rules_meta:
            group_id = group["id"]
            group_name = group["name"]
            is_gate = group.get("is_gate", False)

            for sr in group.get("sub_rules", []):
                cf = sr.get("config_file")
                config_type = sr.get("config_type")
                enabled = sr.get("enabled", False)
                config_data = None

                if cf:
                    full_path = config_path / cf
                    if not full_path.exists():
                        print(f"[ConfigLoader] Warning: '{full_path}' not found. "
                              f"Rule {sr['id']} auto-disabled.")
                        enabled = False
                    else:
                        config_data = self._load_config_data(cf, config_type, config_path)

                loaded.append(RuleDefinition(
                    id=sr["id"],
                    name=sr["name"],
                    enabled=enabled,
                    is_gate=is_gate,
                    group=group_id,
                    group_name=group_name,
                    config_file=cf,
                    config_type=config_type,
                    required_fields=sr.get("required_fields", []),
                    config_data=config_data,
                ))
        return loaded


config_loader = ConfigLoader()
