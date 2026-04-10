# Cursor Prompt — Licensing Rule Engine (Multi-Licensor, Config-Driven) v4

---

## Core Design Philosophy

- Engine is **licensor-agnostic** — it reads a licensor ID, loads that licensor's config, runs rules.
- All rule parameters live in **config files** (Excel + YAML). Zero Python changes to add a rule parameter or new licensor.
- Config files are **loaded once at startup** into memory. No file I/O during validation.
- The **input file is always uploaded** by the user through Streamlit. No fallbacks.
- Reports are **style-centric** — every row of the input file gets its own result card showing exactly which checks passed, which failed, and why.

---

## Project Structure

```
licensing-validator/
│
├── config/
│   ├── licensor_registry.yml
│   └── disney/
│       ├── sku_suffix_mapping.xlsx        # R2 lookup
│       └── property_hierarchy.xlsx        # R3 lookup (Disney / Marvel / Lucas sheets)
│
├── engine/
│   ├── __init__.py
│   ├── config_loader.py
│   ├── licensor_context.py
│   ├── validator.py
│   └── reporter.py
│
├── rules/
│   ├── __init__.py
│   ├── base_rule.py
│   ├── r1_mandatory_fields.py
│   ├── r2_sku_suffix.py
│   ├── r3_property_validation.py
│   └── rule_registry.py
│
├── ui/
│   └── app.py
│
├── output/                                # created at runtime
└── requirements.txt
```

---

## `config/licensor_registry.yml`

```yaml
licensors:

  disney:
    display_name: "The Walt Disney Company"
    config_path: "config/disney"
    active: true
    rules:

      - id: R1
        name: "Mandatory Field Check"
        enabled: true
        is_gate: true         # gate: failure stops remaining rules for that row
        config_file: null     # R1 reads required_fields directly from this registry
        required_fields:
          - field: "Style #"
            display: "Style Number"
          - field: "Licensor"
            display: "Licensor"
          - field: "Property"
            display: "Property"
          - field: "Art Ref #"
            display: "Art Reference Number"
          - field: "Item Type"
            display: "Item Type"
          - field: "Customer"
            display: "Customer"
          - field: "Division"
            display: "Division"

      - id: R2
        name: "SKU Suffix Validation"
        enabled: true
        is_gate: false
        config_file: "sku_suffix_mapping.xlsx"

      - id: R3
        name: "Property Validation"
        enabled: true
        is_gate: false
        config_file: "property_hierarchy.xlsx"
        # R3 checks two things from this file (both text-based):
        # 1. Does the declared Property exist in the approved hierarchy?
        # 2. Is the Property flagged DO NOT USE?
        # Art Ref cross-check (requires DMC portal) is out of scope for this phase.

  # To add a new licensor: add a block here and create its config folder.
  # To disable a rule: set enabled: false. No Python changes needed.
  # To add a required field to R1: add an entry under required_fields.
```

---

## `engine/config_loader.py`

```python
"""
Loads all licensor config at startup. Called once via st.cache_resource.
All validation-time access is in-memory dict lookup only.
"""
import yaml
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field as dc_field


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
```

---

## `engine/licensor_context.py`

```python
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
```

---

## `rules/base_rule.py`

```python
from abc import ABC, abstractmethod
import pandas as pd

class BaseRule(ABC):
    rule_id: str
    rule_name: str

    @abstractmethod
    def validate(self, row: pd.Series, context: dict) -> dict:
        """
        Returns:
        {
            "rule_id":   str,
            "rule_name": str,
            "status":    "PASS" | "FAIL",
            "reason":    str | None
        }
        """
        pass

    def _pass(self) -> dict:
        return {"rule_id": self.rule_id, "rule_name": self.rule_name,
                "status": "PASS", "reason": None}

    def _fail(self, reason: str) -> dict:
        return {"rule_id": self.rule_id, "rule_name": self.rule_name,
                "status": "FAIL", "reason": reason}
```

---

## `rules/r1_mandatory_fields.py`

```python
"""
R1 — Mandatory Field Check
Required fields come from context["rules"]["R1"].required_fields (registry YAML).
No hardcoded field names in this file.
"""
import pandas as pd
from rules.base_rule import BaseRule

class R1MandatoryFields(BaseRule):
    rule_id   = "R1"
    rule_name = "Mandatory Field Check"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R1")
        if not rule_def:
            return self._fail("R1 rule definition missing from context")

        missing = []
        for fld in rule_def.required_fields:
            val = row.get(fld["field"], None)
            if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == "":
                missing.append(fld["display"])

        if missing:
            return self._fail(f"Missing required fields: {', '.join(missing)}")
        return self._pass()
```

---

## `rules/r2_sku_suffix.py`

```python
"""
R2 — SKU Suffix Validation
Suffix map comes from context["rules"]["R2"].config_data (DataFrame).
Loaded from sku_suffix_mapping.xlsx. No hardcoded values.
"""
import pandas as pd
from rules.base_rule import BaseRule

class R2SKUSuffix(BaseRule):
    rule_id   = "R2"
    rule_name = "SKU Suffix Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R2")
        if not rule_def or rule_def.config_data is None:
            return self._fail("R2 config (sku_suffix_mapping.xlsx) not loaded")

        sku = str(row.get("Style #", "")).strip()
        if len(sku) < 3:
            return self._fail(f"Style # '{sku}' too short to extract suffix (needs ≥ 3 chars)")

        suffix = sku[-3:].upper()
        df: pd.DataFrame = rule_def.config_data.copy()
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        match = df[df["suffix_code"].str.strip().str.upper() == suffix]
        if match.empty:
            valid = sorted(df["suffix_code"].str.strip().str.upper().tolist())
            return self._fail(
                f"Suffix '{suffix}' not in approved list. Valid suffixes: {', '.join(valid)}"
            )
        return self._pass()
```

---

## `rules/r3_property_validation.py`

```python
"""
R3 — Property Validation (text-based checks only)

Uses property_hierarchy.xlsx which has three sheets: Disney, Marvel, Lucas.
config_data is a dict of DataFrames: {"Disney": df, "Marvel": df, "Lucas": df}

Checks performed (both text-only, no portal access needed):
  1. Does the declared Property exist in any sheet of the hierarchy?
  2. Is the Property flagged as DO NOT USE?

Out of scope for this phase: Art Ref # cross-check (requires DMC portal).
"""
import pandas as pd
from rules.base_rule import BaseRule

class R3PropertyValidation(BaseRule):
    rule_id   = "R3"
    rule_name = "Property Validation"

    def validate(self, row: pd.Series, context: dict) -> dict:
        rule_def = context["rules"].get("R3")
        if not rule_def or rule_def.config_data is None:
            return self._fail("R3 config (property_hierarchy.xlsx) not loaded")

        declared = str(row.get("Property", "")).strip()
        if not declared:
            # R1 should have caught this, but guard anyway
            return self._fail("Property field is empty")

        hierarchy: dict = rule_def.config_data  # {"Disney": df, "Marvel": df, "Lucas": df}

        # Search across all sheets
        found_row = None
        found_sheet = None
        for sheet_name, df in hierarchy.items():
            df.columns = df.columns.str.strip()
            # Normalise property names for comparison (strip, lower)
            df["_norm"] = df["Property"].astype(str).str.strip().str.lower()
            declared_norm = declared.lower()
            match = df[df["_norm"] == declared_norm]
            if not match.empty:
                found_row = match.iloc[0]
                found_sheet = sheet_name
                break

        if found_row is None:
            return self._fail(
                f"Property '{declared}' not found in approved property hierarchy. "
                f"Check spelling or confirm the property is licensed."
            )

        # Check DO NOT USE flag — column header may vary, handle both None and string
        do_not_use_val = found_row.get("DO NOT USE", None)
        if do_not_use_val is not None and str(do_not_use_val).strip().lower() not in ("", "nan", "none"):
            return self._fail(
                f"Property '{declared}' is flagged DO NOT USE: {str(do_not_use_val).strip()}"
            )

        return self._pass()
```

---

## `rules/rule_registry.py`

```python
from rules.r1_mandatory_fields import R1MandatoryFields
from rules.r2_sku_suffix import R2SKUSuffix
from rules.r3_property_validation import R3PropertyValidation

RULE_REGISTRY: dict = {
    "R1": R1MandatoryFields(),
    "R2": R2SKUSuffix(),
    "R3": R3PropertyValidation(),
    # Future rules registered here when implemented
}
```

---

## `engine/validator.py`

```python
import pandas as pd
from rules.rule_registry import RULE_REGISTRY

def run_validation(df: pd.DataFrame, context: dict) -> list[dict]:
    """
    Returns one result dict per input row.
    Gate rule failure: remaining rules for that row get status SKIP.
    """
    active_rule_ids = context["active_rule_ids"]
    gate_rule_ids   = context["gate_rule_ids"]
    results = []

    for idx, row in df.iterrows():
        row_results = []
        overall = "PASS"
        gate_failed = False

        for rule_id in active_rule_ids:
            rule_def  = context["rules"].get(rule_id)
            rule_name = rule_def.name if rule_def else rule_id

            if gate_failed:
                row_results.append({
                    "rule_id": rule_id, "rule_name": rule_name,
                    "status": "SKIP", "reason": "Skipped — upstream gate rule failed"
                })
                continue

            if rule_id not in RULE_REGISTRY:
                print(f"[Validator] '{rule_id}' active in config but not in RULE_REGISTRY. Skipping.")
                continue

            result = RULE_REGISTRY[rule_id].validate(row, context)
            row_results.append(result)

            if result["status"] == "FAIL":
                overall = "FAIL"
                if rule_id in gate_rule_ids:
                    gate_failed = True

        results.append({
            "row_index":      idx,
            "Style #":        str(row.get("Style #", "")),
            "Property":       str(row.get("Property", "")),
            "Licensor":       str(row.get("Licensor", "")),
            "Item Type":      str(row.get("Item Type", "")),
            "Customer":       str(row.get("Customer", "")),
            "results":        row_results,
            "overall_status": overall,
        })

    return results
```

---

## `engine/reporter.py`

```python
import pandas as pd
from datetime import datetime

def build_output(
    df: pd.DataFrame,
    validation_results: list[dict]
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Returns:
      pass_df   — rows where all rules passed
      error_df  — rows where one or more rules failed
      summary   — aggregate stats + per-style detail for UI rendering
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pass_rows, error_rows = [], []

    for vr in validation_results:
        original = df.loc[vr["row_index"]].to_dict()
        base = {**original, "run_timestamp": timestamp}
        failed = [r for r in vr["results"] if r["status"] == "FAIL"]

        if vr["overall_status"] == "PASS":
            pass_rows.append({**base, "validation_status": "PASS"})
        else:
            error_rows.append({
                **base,
                "validation_status": "FAIL",
                "failed_rules":    ", ".join(r["rule_id"] for r in failed),
                "failure_reasons": " | ".join(
                    f"{r['rule_id']}: {r['reason']}" for r in failed if r["reason"]
                ),
            })

    pass_df  = pd.DataFrame(pass_rows)  if pass_rows  else pd.DataFrame()
    error_df = pd.DataFrame(error_rows) if error_rows else pd.DataFrame()

    total      = len(validation_results)
    pass_count = len(pass_rows)
    fail_count = len(error_rows)
    pass_pct   = round(pass_count / total * 100, 1) if total > 0 else 0.0

    # Per-rule aggregate stats
    rule_stats: dict[str, dict] = {}
    for vr in validation_results:
        for r in vr["results"]:
            rid = r["rule_id"]
            if rid not in rule_stats:
                rule_stats[rid] = {"name": r["rule_name"], "pass": 0, "fail": 0, "skip": 0}
            rule_stats[rid][r["status"].lower()] += 1

    summary = {
        "total":            total,
        "pass_count":       pass_count,
        "fail_count":       fail_count,
        "pass_pct":         pass_pct,
        "timestamp":        timestamp,
        "rule_stats":       rule_stats,
        "per_style":        validation_results,   # full row-level detail for style cards
    }

    return pass_df, error_df, summary
```

---

## `ui/app.py` — Full Specification

### Startup & Config Init

```python
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io, time
from engine.config_loader import config_loader
from engine.licensor_context import build_context
from engine.validator import run_validation
from engine.reporter import build_output

st.set_page_config(page_title="Licensing Rule Engine", page_icon="✅", layout="wide")

@st.cache_resource
def initialise_configs():
    config_loader.load_all()
    return config_loader

cfg_loader = initialise_configs()
```

---

### Sidebar Navigation

```python
page = st.sidebar.radio("Navigation", ["🔍 Validate", "📋 Report", "⚙️ Config"])
```

---

### Page 1 — Validate

#### Licensor selector + file upload

```python
licensor_options = cfg_loader.available_licensors()   # [(id, display_name)]
label_to_id = {display: lid for lid, display in licensor_options}
selected_display = st.selectbox("Licensor", [d for _, d in licensor_options])
selected_id = label_to_id[selected_display]

uploaded_file = st.file_uploader(
    "Upload Centric Export (.xlsx)",
    type=["xlsx"],
    help="Export your styles from Centric PLM and upload here."
)

if uploaded_file is None:
    st.info("Upload a Centric export file to begin.")
    st.stop()

df = pd.read_excel(uploaded_file)
st.caption(f"Loaded: **{len(df)} rows** · {len(df.columns)} columns")
```

#### Animated validation run

When the user clicks **Run Validation**, show an animated step-by-step progress sequence
before displaying results. This is the most important UI moment — make it feel like the
engine is actually thinking through each rule.

```python
if st.button("▶ Run Validation", type="primary", use_container_width=True):

    context = build_context(selected_id)
    active_rules = context["active_rule_ids"]

    # ── Animated rule-check sequence ──────────────────────────────────────────
    st.markdown("### Checking rules...")
    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    rule_status_cols = st.columns(len(active_rules))

    # Render each rule badge as "pending" initially
    rule_badges = {}
    for i, rule_id in enumerate(active_rules):
        rule_def = context["rules"][rule_id]
        with rule_status_cols[i]:
            rule_badges[rule_id] = st.empty()
            rule_badges[rule_id].markdown(
                f"""<div style='text-align:center; padding:12px; border-radius:10px;
                background:#f0f0f0; color:#888; font-size:13px;'>
                ⏳<br><b>{rule_id}</b><br>{rule_def.name}</div>""",
                unsafe_allow_html=True
            )

    # Run validation (actual computation)
    with st.spinner("Running..."):
        v_results = run_validation(df, context)
        pass_df, error_df, summary = build_output(df, v_results)

    # Animate each rule badge updating from pending → result
    rule_stats = summary["rule_stats"]
    for i, rule_id in enumerate(active_rules):
        rule_def = context["rules"][rule_id]
        stats = rule_stats.get(rule_id, {"pass": 0, "fail": 0, "skip": 0})
        has_fail = stats["fail"] > 0

        status_placeholder.markdown(
            f"**Checking {rule_id} — {rule_def.name}...**"
        )
        time.sleep(0.6)   # animation delay per rule

        color  = "#d4edda" if not has_fail else "#f8d7da"
        border = "#28a745" if not has_fail else "#dc3545"
        icon   = "✅" if not has_fail else "❌"
        label  = f"{stats['pass']} passed" if not has_fail else f"{stats['fail']} failed"

        rule_badges[rule_id].markdown(
            f"""<div style='text-align:center; padding:12px; border-radius:10px;
            background:{color}; border:2px solid {border}; font-size:13px;'>
            {icon}<br><b>{rule_id}</b><br>{rule_def.name}<br>
            <span style='font-size:11px;color:#555'>{label}</span></div>""",
            unsafe_allow_html=True
        )
        progress_bar.progress((i + 1) / len(active_rules))
        time.sleep(0.3)

    status_placeholder.markdown("✅ **Validation complete.**")
    # ── End animation ─────────────────────────────────────────────────────────

    st.session_state["last_run"] = {
        "v_results": v_results, "pass_df": pass_df,
        "error_df": error_df, "summary": summary,
        "context": context, "licensor": selected_display,
        "filename": uploaded_file.name,
    }
    st.rerun()  # refresh to show results cleanly without the animation placeholders
```

#### Summary metrics (shown after run)

```python
if "last_run" in st.session_state:
    run = st.session_state["last_run"]
    s   = run["summary"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Styles",  s["total"])
    col2.metric("✅ Passed",     s["pass_count"])
    col3.metric("❌ Failed",     s["fail_count"])
    col4.metric("Pass Rate",     f"{s['pass_pct']}%")

    st.divider()

    # Per-rule aggregate row
    st.markdown("**Rule breakdown**")
    rule_row_data = []
    for rid, stats in s["rule_stats"].items():
        total_checked = stats["pass"] + stats["fail"]
        pct = round(stats["pass"] / total_checked * 100, 1) if total_checked > 0 else 0
        rule_row_data.append({
            "Rule": rid,
            "Name": stats["name"],
            "✅ Passed": stats["pass"],
            "❌ Failed": stats["fail"],
            "⏭ Skipped": stats["skip"],
            "Pass Rate": f"{pct}%",
        })
    st.dataframe(pd.DataFrame(rule_row_data), use_container_width=True, hide_index=True)

    st.divider()
```

#### Style-centric results — one card per input row

This is the core of the report. Each style gets its own result card.

```python
    st.markdown("### Results by Style")

    # Filter tabs
    view_filter = st.radio("Show", ["All", "✅ Passed only", "❌ Failed only"],
                            horizontal=True)

    for vr in s["per_style"]:
        if view_filter == "✅ Passed only" and vr["overall_status"] != "PASS":
            continue
        if view_filter == "❌ Failed only" and vr["overall_status"] != "FAIL":
            continue

        is_pass    = vr["overall_status"] == "PASS"
        card_color = "#f0faf4" if is_pass else "#fff5f5"
        border_col = "#28a745" if is_pass else "#dc3545"
        badge      = "✅ PASS" if is_pass else "❌ FAIL"
        badge_bg   = "#28a745" if is_pass else "#dc3545"

        # Style card header
        st.markdown(
            f"""<div style='background:{card_color}; border-left:5px solid {border_col};
            border-radius:8px; padding:16px 20px; margin-bottom:6px;'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
              <div>
                <span style='font-size:16px; font-weight:600;'>{vr["Style #"]}</span>
                <span style='color:#555; margin-left:12px; font-size:14px;'>{vr["Property"]}</span>
                <span style='color:#888; margin-left:8px; font-size:13px;'>·  {vr["Item Type"]}  ·  {vr["Customer"]}</span>
              </div>
              <span style='background:{badge_bg}; color:white; padding:4px 14px;
              border-radius:20px; font-size:13px; font-weight:600;'>{badge}</span>
            </div>
            </div>""",
            unsafe_allow_html=True
        )

        # Rule checks inline — one row per rule
        for r in vr["results"]:
            s_icon  = "✅" if r["status"] == "PASS" else ("❌" if r["status"] == "FAIL" else "⏭")
            s_color = "#155724" if r["status"] == "PASS" else ("#721c24" if r["status"] == "FAIL" else "#856404")
            s_bg    = "#d4edda" if r["status"] == "PASS" else ("#f8d7da" if r["status"] == "FAIL" else "#fff3cd")

            reason_html = (
                f"<span style='color:{s_color}; font-size:12px; margin-left:8px;'>→ {r['reason']}</span>"
                if r["reason"] else ""
            )
            st.markdown(
                f"""<div style='background:{s_bg}; border-radius:6px; padding:8px 16px;
                margin:3px 0 3px 24px; display:flex; align-items:center;'>
                <span style='font-weight:600; color:{s_color}; min-width:40px;'>{s_icon} {r["rule_id"]}</span>
                <span style='color:{s_color}; margin-left:8px; font-size:13px;'>{r["rule_name"]}</span>
                {reason_html}
                </div>""",
                unsafe_allow_html=True
            )

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)
```

#### Download buttons

```python
    st.divider()
    st.markdown("**Download reports**")
    col1, col2, col3 = st.columns(3)

    if not run["pass_df"].empty:
        buf = io.BytesIO()
        run["pass_df"].to_excel(buf, index=False, engine="openpyxl")
        col1.download_button("⬇️ Pass Report", buf.getvalue(),
                             file_name="pass_report.xlsx",
                             mime="application/vnd.ms-excel")

    if not run["error_df"].empty:
        buf = io.BytesIO()
        run["error_df"].to_excel(buf, index=False, engine="openpyxl")
        col2.download_button("⬇️ Error Report", buf.getvalue(),
                             file_name="error_report.xlsx",
                             mime="application/vnd.ms-excel")

    # Full combined report — two sheets
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        if not run["pass_df"].empty:
            run["pass_df"].to_excel(writer, sheet_name="Pass", index=False)
        if not run["error_df"].empty:
            run["error_df"].to_excel(writer, sheet_name="Errors", index=False)
    col3.download_button(
        "⬇️ Full Report (.xlsx)",
        buf.getvalue(),
        file_name=f"validation_report_{s['timestamp'].replace(':', '-').replace(' ', '_')}.xlsx",
        mime="application/vnd.ms-excel",
    )
```

---

### Page 2 — Report

Full summary page. Only shown if `st.session_state["last_run"]` exists.

```python
if "last_run" not in st.session_state:
    st.info("Run a validation first to see the report.")
    st.stop()

run = st.session_state["last_run"]
s   = run["summary"]

st.title(f"Validation Report — {run['licensor']}")
st.caption(f"File: {run['filename']}  ·  Run at: {s['timestamp']}")
st.divider()
```

#### Donut chart — pass/fail ratio

```python
fig = go.Figure(go.Pie(
    values=[s["pass_count"], s["fail_count"]],
    labels=["Passed", "Failed"],
    hole=0.65,
    marker_colors=["#28a745", "#dc3545"],
    textinfo="label+percent",
    hovertemplate="%{label}: %{value}<extra></extra>",
))
fig.update_layout(
    annotations=[{
        "text": f"<b>{s['pass_pct']}%</b><br>pass rate",
        "x": 0.5, "y": 0.5, "font_size": 18,
        "showarrow": False
    }],
    showlegend=True,
    margin=dict(t=20, b=20, l=20, r=20),
    height=320,
)
st.plotly_chart(fig, use_container_width=True)
st.divider()
```

#### Per-rule cards

```python
st.markdown("### Rule-by-rule breakdown")

for rid, stats in s["rule_stats"].items():
    total_checked = stats["pass"] + stats["fail"]
    pct = round(stats["pass"] / total_checked * 100, 1) if total_checked > 0 else 0
    has_fail = stats["fail"] > 0
    border = "#dc3545" if has_fail else "#28a745"

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        c1.markdown(f"**{rid} — {stats['name']}**")
        c2.metric("✅ Passed",  stats["pass"])
        c3.metric("❌ Failed",  stats["fail"])
        c4.metric("Pass Rate",  f"{pct}%")

        if has_fail:
            # List every failed style for this rule
            failed_styles = [
                vr for vr in s["per_style"]
                if any(r["rule_id"] == rid and r["status"] == "FAIL" for r in vr["results"])
            ]
            st.markdown("**Failed styles:**")
            for vr in failed_styles:
                reason = next(
                    (r["reason"] for r in vr["results"] if r["rule_id"] == rid), ""
                )
                st.markdown(
                    f"- `{vr['Style #']}` &nbsp; **{vr['Property']}** &nbsp;→ {reason}"
                )
```

---

### Page 3 — Config (read-only)

```python
st.title("Active Configuration")
st.caption("Read-only view of rules loaded from licensor_registry.yml")

for lid, display in cfg_loader.available_licensors():
    cfg = cfg_loader.get_config(lid)
    st.subheader(display)
    rows = [{
        "ID":          r.id,
        "Name":        r.name,
        "Enabled":     "✅" if r.enabled else "❌",
        "Gate Rule":   "🔒 Yes" if r.is_gate else "—",
        "Config File": r.config_file or "—",
    } for r in cfg.rules]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
```

---

## requirements.txt

```
streamlit>=1.32.0
pandas>=2.0.0
openpyxl>=3.1.0
pyyaml>=6.0
plotly>=5.0.0
```

---

## Build Order

1. `config/licensor_registry.yml`
2. `engine/config_loader.py` — test:
   ```bash
   python -c "from engine.config_loader import config_loader; config_loader.load_all()"
   ```
3. `engine/licensor_context.py`
4. `rules/base_rule.py`
5. `rules/r1_mandatory_fields.py`
6. `rules/r2_sku_suffix.py`
7. `rules/r3_property_validation.py`
8. `rules/rule_registry.py`
9. `engine/validator.py`
10. `engine/reporter.py`
11. `ui/app.py`

---

## Config Change Reference (No Python Required)

| What to change | Where |
|----------------|-------|
| Add a required field to R1 | `required_fields` block in registry YAML |
| Enable/disable any rule | `enabled: true/false` in registry YAML |
| Make a rule a gate | `is_gate: true` in registry YAML |
| Add a suffix code | Edit `config/disney/sku_suffix_mapping.xlsx` |
| Add a property | Edit `config/disney/property_hierarchy.xlsx` |
| Add a new licensor | New block in registry YAML + new config folder |

---

## Out of Scope

- Creating config Excel files (team places them manually)
- Sample/demo data — user always uploads their own file
- R4–R9 (future phases)
- Art Ref # cross-check for R3 (requires DMC portal — future)
- Portal login / submission automation
- Authentication

---

*End of prompt. Build in the order specified.*