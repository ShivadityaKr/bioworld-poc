from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
os.chdir(_PROJECT_ROOT)

import gradio as gr
import pandas as pd

from engine.config_loader import config_loader
from engine.licensor_context import build_context
from engine.reporter import build_output
from engine.validator import run_validation

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
config_loader.load_all()

_licensor_options = config_loader.available_licensors()
_licensor_map = {display: lid for lid, display in _licensor_options}
_licensor_names = [d for _, d in _licensor_options]


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------
def run(licensor_display: str, file_obj):
    if file_obj is None:
        raise gr.Error("Upload a Centric export (.xlsx) first.")

    licensor_id = _licensor_map.get(licensor_display)
    if not licensor_id:
        raise gr.Error("Select a valid licensor.")

    df = pd.read_excel(file_obj.name if hasattr(file_obj, "name") else file_obj)
    context = build_context(licensor_id)
    v_results = run_validation(df, context)
    _pass_df, _error_df, summary = build_output(df, v_results)

    total = summary["total"]
    pass_count = summary["pass_count"]
    fail_count = summary["fail_count"]
    pass_pct = summary["pass_pct"]

    # -- Build style-centric HTML (ALL styles) -----------------------------
    html_parts = []

    html_parts.append(f"""
    <div style="display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap;">
      <div style="flex:1; min-width:140px; background:#f8f9fa; border-radius:12px;
           padding:20px; text-align:center; border:1px solid #e9ecef;">
        <div style="font-size:28px; font-weight:700; color:#333;">{total}</div>
        <div style="font-size:13px; color:#666; margin-top:4px;">Total Styles</div>
      </div>
      <div style="flex:1; min-width:140px; background:#f0faf4; border-radius:12px;
           padding:20px; text-align:center; border:1px solid #c3e6cb;">
        <div style="font-size:28px; font-weight:700; color:#28a745;">{pass_count}</div>
        <div style="font-size:13px; color:#666; margin-top:4px;">Passed</div>
      </div>
      <div style="flex:1; min-width:140px; background:#fff5f5; border-radius:12px;
           padding:20px; text-align:center; border:1px solid #f5c6cb;">
        <div style="font-size:28px; font-weight:700; color:#dc3545;">{fail_count}</div>
        <div style="font-size:13px; color:#666; margin-top:4px;">Failed</div>
      </div>
      <div style="flex:1; min-width:140px; background:#f8f9fa; border-radius:12px;
           padding:20px; text-align:center; border:1px solid #e9ecef;">
        <div style="font-size:28px; font-weight:700; color:#0066cc;">{pass_pct}%</div>
        <div style="font-size:13px; color:#666; margin-top:4px;">Pass Rate</div>
      </div>
    </div>
    """)

    for vr in v_results:
        style_num = vr["Style #"]
        prop = vr["Property"]
        item_type = vr["Item Type"]
        customer = vr["Customer"]
        overall = vr["overall_status"]
        results = vr["results"]

        rules_passed = sum(1 for r in results if r["status"] == "PASS")
        rules_failed = sum(1 for r in results if r["status"] == "FAIL")
        rules_skipped = sum(1 for r in results if r["status"] == "SKIP")

        is_pass = overall == "PASS"
        card_bg = "#f0faf4" if is_pass else "#fff5f5"
        border_color = "#28a745" if is_pass else "#dc3545"
        badge_bg = "#28a745" if is_pass else "#dc3545"
        badge_text = "PASS" if is_pass else "FAIL"

        score_parts = []
        if rules_passed:
            score_parts.append(f'<span style="color:#28a745;font-weight:600;">{rules_passed} passed</span>')
        if rules_failed:
            score_parts.append(f'<span style="color:#dc3545;font-weight:600;">{rules_failed} failed</span>')
        if rules_skipped:
            score_parts.append(f'<span style="color:#856404;font-weight:600;">{rules_skipped} skipped</span>')
        score_html = " &middot; ".join(score_parts)

        card_html = f"""
        <div style="background:{card_bg};border-left:5px solid {border_color};
             border-radius:10px;padding:18px 22px;margin-bottom:12px;
             box-shadow:0 1px 3px rgba(0,0,0,0.06);">
          <div style="display:flex;justify-content:space-between;align-items:center;
               margin-bottom:10px;flex-wrap:wrap;gap:8px;">
            <div>
              <span style="font-size:17px;font-weight:700;color:#222;">{style_num}</span>
              <span style="color:#555;margin-left:14px;font-size:14px;">{prop}</span>
              <span style="color:#999;margin-left:10px;font-size:13px;">{item_type} &middot; {customer}</span>
            </div>
            <div style="display:flex;align-items:center;gap:12px;">
              <span style="font-size:12px;color:#555;">{score_html}</span>
              <span style="background:{badge_bg};color:white;padding:5px 16px;
                    border-radius:20px;font-size:13px;font-weight:700;
                    letter-spacing:0.5px;">{badge_text}</span>
            </div>
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;">
        """

        for r in results:
            status = r["status"]
            if status == "PASS":
                icon, bg, color = "&#10003;", "#d4edda", "#155724"
            elif status == "FAIL":
                icon, bg, color = "&#10007;", "#f8d7da", "#721c24"
            else:
                icon, bg, color = "&#8674;", "#fff3cd", "#856404"

            reason_html = ""
            if r["reason"]:
                reason_html = (
                    f'<span style="color:{color};font-size:12px;margin-left:10px;'
                    f'opacity:0.85;">&rarr; {r["reason"]}</span>'
                )

            card_html += f"""
            <div style="background:{bg};border-radius:6px;padding:8px 14px;
                 display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
              <span style="font-weight:700;color:{color};min-width:55px;font-size:13px;">
                {icon} {r["rule_id"]}
              </span>
              <span style="color:{color};font-size:13px;">{r["rule_name"]}</span>
              {reason_html}
            </div>
            """

        card_html += "</div></div>"
        html_parts.append(card_html)

    results_html = "\n".join(html_parts)

    # -- Build single downloadable report ----------------------------------
    report_rows = []
    for vr in v_results:
        check_lines = []
        for r in vr["results"]:
            line = f"[{r['status']}] {r['rule_id']} - {r['rule_name']}"
            if r["reason"]:
                line += f" : {r['reason']}"
            check_lines.append(line)

        report_rows.append({
            "Style #": vr["Style #"],
            "Property": vr["Property"],
            "Item Type": vr["Item Type"],
            "Customer": vr["Customer"],
            "Licensor": vr["Licensor"],
            "Status": vr["overall_status"],
            "Checks Passed": sum(1 for r in vr["results"] if r["status"] == "PASS"),
            "Checks Failed": sum(1 for r in vr["results"] if r["status"] == "FAIL"),
            "Checks Skipped": sum(1 for r in vr["results"] if r["status"] == "SKIP"),
            "Check Details": "\n".join(check_lines),
        })

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = os.path.join(tempfile.gettempdir(), f"validation_report_{ts}.xlsx")
    report_df = pd.DataFrame(report_rows)
    report_df.to_excel(report_path, index=False, engine="openpyxl")

    # Widen the "Check Details" column and enable text wrap
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment

    wb = load_workbook(report_path)
    ws = wb.active
    detail_col_letter = None
    for col_idx, cell in enumerate(ws[1], 1):
        if cell.value == "Check Details":
            detail_col_letter = cell.column_letter
            break
    if detail_col_letter:
        ws.column_dimensions[detail_col_letter].width = 80
        for row in ws.iter_rows(min_row=2, min_col=ws[detail_col_letter + "1"].column,
                                max_col=ws[detail_col_letter + "1"].column):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(report_path)

    return results_html, gr.update(value=report_path, visible=True)


# ---------------------------------------------------------------------------
# Config view
# ---------------------------------------------------------------------------
def build_config_html():
    parts = []
    for lid, display in _licensor_options:
        cfg = config_loader.get_config(lid)
        parts.append(f"""
        <div style="margin-bottom:24px;">
          <h3 style="margin:0 0 12px 0; color:#333;">{display}</h3>
          <table style="width:100%; border-collapse:collapse; font-size:14px;">
            <thead>
              <tr style="background:#2c3e50; text-align:left;">
                <th style="padding:10px 14px; border-bottom:2px solid #dee2e6; color:#fff;">ID</th>
                <th style="padding:10px 14px; border-bottom:2px solid #dee2e6; color:#fff;">Rule Name</th>
                <th style="padding:10px 14px; border-bottom:2px solid #dee2e6; color:#fff;">Enabled</th>
                <th style="padding:10px 14px; border-bottom:2px solid #dee2e6; color:#fff;">Gate</th>
                <th style="padding:10px 14px; border-bottom:2px solid #dee2e6; color:#fff;">Config File</th>
              </tr>
            </thead>
            <tbody>
        """)
        for r in cfg.rules:
            en_badge = ('<span style="color:#28a745; font-weight:600;">Enabled</span>'
                        if r.enabled else
                        '<span style="color:#dc3545; font-weight:600;">Disabled</span>')
            gate_badge = ('<span style="background:#ffeeba; padding:2px 8px; border-radius:4px;'
                          ' font-size:12px;">Gate</span>' if r.is_gate else "\u2014")
            cf = r.config_file or "\u2014"
            parts.append(f"""
              <tr style="border-bottom:1px solid #e9ecef;">
                <td style="padding:10px 14px; font-weight:600;">{r.id}</td>
                <td style="padding:10px 14px;">{r.name}</td>
                <td style="padding:10px 14px;">{en_badge}</td>
                <td style="padding:10px 14px;">{gate_badge}</td>
                <td style="padding:10px 14px; font-size:12px; color:#666;">{cf}</td>
              </tr>
            """)
        parts.append("</tbody></table></div>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------
css = """
.gradio-container { max-width: 1100px !important; }
#results-area, #results-area > div, .full-scroll, .full-scroll > div {
    max-height: none !important;
    overflow: visible !important;
    height: auto !important;
}
"""

with gr.Blocks(
    title="BioWorld Licensing Rule Engine",
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
    css=css,
) as app:

    gr.Markdown(
        "# BioWorld Licensing Rule Engine\n"
        "Upload a Centric PLM export, pick a licensor, and validate every style "
        "against the configured licensing rules."
    )

    with gr.Tabs():
        # ── Tab 1: Validate ───────────────────────────────────────────────
        with gr.Tab("Validate"):
            with gr.Row():
                licensor_dd = gr.Dropdown(
                    choices=_licensor_names,
                    value=_licensor_names[0] if _licensor_names else None,
                    label="Licensor",
                    scale=1,
                )
                file_upload = gr.File(
                    label="Upload Centric Export (.xlsx)",
                    file_types=[".xlsx"],
                    scale=2,
                )

            with gr.Row():
                run_btn = gr.Button("Run Validation", variant="primary", size="lg", scale=3)
                download_file = gr.File(
                    label="Download Report",
                    visible=False,
                    interactive=False,
                    scale=2,
                )

            results_html = gr.HTML(
                elem_id="results-area",
                value="<div style='text-align:center; padding:40px; color:#999;'>"
                      "Upload a file and click <b>Run Validation</b> to see results.</div>",
                elem_classes=["full-scroll"],
            )

            run_btn.click(
                fn=run,
                inputs=[licensor_dd, file_upload],
                outputs=[results_html, download_file],
            )

        # ── Tab 2: Config ─────────────────────────────────────────────────
        with gr.Tab("Config"):
            gr.Markdown("### Active Configuration\nRead-only view of rules loaded from `licensor_registry.yml`.")
            gr.HTML(value=build_config_html())


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860)
