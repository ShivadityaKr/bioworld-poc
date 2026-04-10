import io
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine.config_loader import config_loader
from engine.licensor_context import build_context
from engine.reporter import build_output
from engine.validator import run_validation

st.set_page_config(page_title="Licensing Rule Engine", page_icon="✅", layout="wide")


@st.cache_resource
def initialise_configs():
    config_loader.load_all()
    return config_loader


cfg_loader = initialise_configs()

page = st.sidebar.radio("Navigation", ["🔍 Validate", "📋 Report", "⚙️ Config"])

if page == "🔍 Validate":
    licensor_options = cfg_loader.available_licensors()
    label_to_id = {display: lid for lid, display in licensor_options}
    selected_display = st.selectbox("Licensor", [d for _, d in licensor_options])
    selected_id = label_to_id[selected_display]

    uploaded_file = st.file_uploader(
        "Upload Centric Export (.xlsx)",
        type=["xlsx"],
        help="Export your styles from Centric PLM and upload here.",
    )

    if uploaded_file is None:
        st.info("Upload a Centric export file to begin.")
    else:
        df = pd.read_excel(uploaded_file)
        st.caption(f"Loaded: **{len(df)} rows** · {len(df.columns)} columns")

        if st.button("▶ Run Validation", type="primary", use_container_width=True):
            context = build_context(selected_id)
            active_rules = context["active_rule_ids"]

            st.markdown("### Checking rules...")
            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            rule_badges = {}
            if not active_rules:
                st.warning("No active rules for this licensor.")
            else:
                rule_status_cols = st.columns(len(active_rules))
                for i, rule_id in enumerate(active_rules):
                    rule_def = context["rules"][rule_id]
                    with rule_status_cols[i]:
                        rule_badges[rule_id] = st.empty()
                        rule_badges[rule_id].markdown(
                            f"""<div style='text-align:center; padding:12px; border-radius:10px;
                            background:#f0f0f0; color:#888; font-size:13px;'>
                            ⏳<br><b>{rule_id}</b><br>{rule_def.name}</div>""",
                            unsafe_allow_html=True,
                        )

            with st.spinner("Running..."):
                v_results = run_validation(df, context)
                pass_df, error_df, summary = build_output(df, v_results)

            if active_rules:
                rule_stats = summary["rule_stats"]
                for i, rule_id in enumerate(active_rules):
                    rule_def = context["rules"][rule_id]
                    stats = rule_stats.get(rule_id, {"pass": 0, "fail": 0, "skip": 0})
                    has_fail = stats["fail"] > 0

                    status_placeholder.markdown(
                        f"**Checking {rule_id} — {rule_def.name}...**"
                    )
                    time.sleep(0.6)

                    color = "#d4edda" if not has_fail else "#f8d7da"
                    border = "#28a745" if not has_fail else "#dc3545"
                    icon = "✅" if not has_fail else "❌"
                    label = f"{stats['pass']} passed" if not has_fail else f"{stats['fail']} failed"

                    rule_badges[rule_id].markdown(
                        f"""<div style='text-align:center; padding:12px; border-radius:10px;
                        background:{color}; border:2px solid {border}; font-size:13px;'>
                        {icon}<br><b>{rule_id}</b><br>{rule_def.name}<br>
                        <span style='font-size:11px;color:#555'>{label}</span></div>""",
                        unsafe_allow_html=True,
                    )
                    progress_bar.progress((i + 1) / len(active_rules))
                    time.sleep(0.3)

                status_placeholder.markdown("✅ **Validation complete.**")

            st.session_state["last_run"] = {
                "v_results": v_results,
                "pass_df": pass_df,
                "error_df": error_df,
                "summary": summary,
                "context": context,
                "licensor": selected_display,
                "filename": uploaded_file.name,
            }
            st.rerun()

        if "last_run" in st.session_state:
            run = st.session_state["last_run"]
            s = run["summary"]

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Styles", s["total"])
            col2.metric("✅ Passed", s["pass_count"])
            col3.metric("❌ Failed", s["fail_count"])
            col4.metric("Pass Rate", f"{s['pass_pct']}%")

            st.divider()

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

            st.markdown("### Results by Style")

            view_filter = st.radio(
                "Show",
                ["All", "✅ Passed only", "❌ Failed only"],
                horizontal=True,
            )

            for vr in s["per_style"]:
                if view_filter == "✅ Passed only" and vr["overall_status"] != "PASS":
                    continue
                if view_filter == "❌ Failed only" and vr["overall_status"] != "FAIL":
                    continue

                is_pass = vr["overall_status"] == "PASS"
                card_color = "#f0faf4" if is_pass else "#fff5f5"
                border_col = "#28a745" if is_pass else "#dc3545"
                badge = "✅ PASS" if is_pass else "❌ FAIL"
                badge_bg = "#28a745" if is_pass else "#dc3545"

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
                    unsafe_allow_html=True,
                )

                for r in vr["results"]:
                    s_icon = "✅" if r["status"] == "PASS" else ("❌" if r["status"] == "FAIL" else "⏭")
                    s_color = "#155724" if r["status"] == "PASS" else ("#721c24" if r["status"] == "FAIL" else "#856404")
                    s_bg = "#d4edda" if r["status"] == "PASS" else ("#f8d7da" if r["status"] == "FAIL" else "#fff3cd")

                    reason_html = (
                        f"<span style='color:{s_color}; font-size:12px; margin-left:8px;'>→ {r['reason']}</span>"
                        if r["reason"]
                        else ""
                    )
                    st.markdown(
                        f"""<div style='background:{s_bg}; border-radius:6px; padding:8px 16px;
                        margin:3px 0 3px 24px; display:flex; align-items:center;'>
                        <span style='font-weight:600; color:{s_color}; min-width:40px;'>{s_icon} {r["rule_id"]}</span>
                        <span style='color:{s_color}; margin-left:8px; font-size:13px;'>{r["rule_name"]}</span>
                        {reason_html}
                        </div>""",
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

            st.divider()
            st.markdown("**Download reports**")
            col1, col2, col3 = st.columns(3)

            if not run["pass_df"].empty:
                buf = io.BytesIO()
                run["pass_df"].to_excel(buf, index=False, engine="openpyxl")
                col1.download_button(
                    "⬇️ Pass Report",
                    buf.getvalue(),
                    file_name="pass_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            if not run["error_df"].empty:
                buf = io.BytesIO()
                run["error_df"].to_excel(buf, index=False, engine="openpyxl")
                col2.download_button(
                    "⬇️ Error Report",
                    buf.getvalue(),
                    file_name="error_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            if not run["pass_df"].empty or not run["error_df"].empty:
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
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                col3.caption("No pass/error rows to combine.")

elif page == "📋 Report":
    if "last_run" not in st.session_state:
        st.info("Run a validation first to see the report.")
    else:
        run = st.session_state["last_run"]
        s = run["summary"]

        st.title(f"Validation Report — {run['licensor']}")
        st.caption(f"File: {run['filename']}  ·  Run at: {s['timestamp']}")
        st.divider()

        fig = go.Figure(
            go.Pie(
                values=[s["pass_count"], s["fail_count"]],
                labels=["Passed", "Failed"],
                hole=0.65,
                marker_colors=["#28a745", "#dc3545"],
                textinfo="label+percent",
                hovertemplate="%{label}: %{value}<extra></extra>",
            )
        )
        fig.update_layout(
            annotations=[{
                "text": f"<b>{s['pass_pct']}%</b><br>pass rate",
                "x": 0.5,
                "y": 0.5,
                "font_size": 18,
                "showarrow": False,
            }],
            showlegend=True,
            margin=dict(t=20, b=20, l=20, r=20),
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.divider()

        st.markdown("### Rule-by-rule breakdown")

        for rid, stats in s["rule_stats"].items():
            total_checked = stats["pass"] + stats["fail"]
            pct = round(stats["pass"] / total_checked * 100, 1) if total_checked > 0 else 0
            has_fail = stats["fail"] > 0

            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.markdown(f"**{rid} — {stats['name']}**")
                c2.metric("✅ Passed", stats["pass"])
                c3.metric("❌ Failed", stats["fail"])
                c4.metric("Pass Rate", f"{pct}%")

                if has_fail:
                    failed_styles = [
                        vr
                        for vr in s["per_style"]
                        if any(r["rule_id"] == rid and r["status"] == "FAIL" for r in vr["results"])
                    ]
                    st.markdown("**Failed styles:**")
                    for vr in failed_styles:
                        reason = next(
                            (r["reason"] for r in vr["results"] if r["rule_id"] == rid),
                            "",
                        )
                        st.markdown(
                            f"- `{vr['Style #']}` &nbsp; **{vr['Property']}** &nbsp;→ {reason}"
                        )

elif page == "⚙️ Config":
    st.title("Active Configuration")
    st.caption("Read-only view of rules loaded from licensor_registry.yml")

    for lid, display in cfg_loader.available_licensors():
        cfg = cfg_loader.get_config(lid)
        st.subheader(display)
        rows = [{
            "ID": r.id,
            "Name": r.name,
            "Enabled": "✅" if r.enabled else "❌",
            "Gate Rule": "🔒 Yes" if r.is_gate else "—",
            "Config File": r.config_file or "—",
        } for r in cfg.rules]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
