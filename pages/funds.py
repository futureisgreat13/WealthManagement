import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("💰 Funds")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)
utils.show_unsaved_warning()
utils.render_year_end_alert("Funds")

items = utils.load_json(utils.DATA_DIR / "funds.json", [])
active = [i for i in items if i.get("status") == "Active"]

# Compute year range
earliest_yr = min((f.get("year_invested", utils.CURRENT_YEAR) for f in items), default=utils.CURRENT_YEAR) if items else utils.CURRENT_YEAR
latest_yr_str = str(utils.CURRENT_YEAR - 1)
all_years = list(range(earliest_yr, utils.CURRENT_YEAR + 6))
all_yr_strs = [str(y) for y in all_years]

# ── CASH FLOW OVERVIEW ──────────────────────────────────────────────────
st.subheader("Cash Flow Overview")
st.caption("Net capital calls (outflow) and distributions (inflow) per year across all funds")

calls_by_year = {}
dist_by_year = {}
for f in items:
    for cs in f.get("capital_call_schedule", []):
        yr = cs.get("year")
        if yr:
            act = cs.get("actual_eur", 0)
            if act is None or (isinstance(act, float) and (act != act)):  # NaN check
                act = 0
            calls_by_year[yr] = calls_by_year.get(yr, 0) + act
    for yr_str, val in f.get("distribution_history", {}).items():
        yr = int(yr_str)
        dist_by_year[yr] = dist_by_year.get(yr, 0) + (val or 0)

cf_years = sorted(set(list(calls_by_year.keys()) + list(dist_by_year.keys())))
if cf_years:
    fig_cf = go.Figure()
    fig_cf.add_trace(go.Bar(
        x=[str(y) for y in cf_years],
        y=[-calls_by_year.get(y, 0) for y in cf_years],
        name="Capital Calls (out)", marker_color="#ff4444",
    ))
    fig_cf.add_trace(go.Bar(
        x=[str(y) for y in cf_years],
        y=[dist_by_year.get(y, 0) for y in cf_years],
        name="Distributions (in)", marker_color="#4CAF50",
    ))
    net_cf = [dist_by_year.get(y, 0) - calls_by_year.get(y, 0) for y in cf_years]
    fig_cf.add_trace(go.Scatter(
        x=[str(y) for y in cf_years], y=net_cf,
        name="Net Cash Flow", mode="lines+markers",
        line=dict(color="#ffa500", width=2), marker=dict(size=5),
    ))
    fig_cf.update_layout(**utils.bloomberg_chart_layout(title="", height=220, barmode="relative",
                         xaxis=dict(title="Year"), yaxis=dict(title="EUR", tickformat=",.0f")))
    st.plotly_chart(fig_cf, use_container_width=True, config={"displayModeBar": False})

    # Summary metrics
    total_calls = sum(calls_by_year.values())
    total_dist = sum(dist_by_year.values())
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Total Capital Calls", utils.fmt_eur(total_calls))
    mc2.metric("Total Distributions", utils.fmt_eur(total_dist))
    mc3.metric("Net Cash Flow", utils.fmt_eur(total_dist - total_calls))
else:
    st.info("No capital call or distribution data yet.")

# KPI bar
import math
def _safe(v):
    """Convert NaN/None/non-numeric to 0."""
    if v is None:
        return 0
    try:
        v = float(v)
        if math.isnan(v) or math.isinf(v):
            return 0
        return v
    except (ValueError, TypeError):
        return 0

total_committed = sum(_safe(i.get("committed_eur", 0)) for i in items)
total_called = sum(_safe(i.get("called_eur", 0)) for i in items)
total_nav = 0
for f in active:
    vh = f.get("value_history", {})
    val = vh.get(latest_yr_str, 0)
    if val <= 0:
        val = f.get("current_nav_eur", 0)
    total_nav += val

c1, c2, c3 = st.columns(3)
c1.metric(f"Current NAV ({latest_yr_str} YE)", utils.fmt_eur(total_nav))
c2.metric("Total Committed", utils.fmt_eur(total_committed))
c3.metric("Total Called", utils.fmt_eur(total_called))

st.divider()

# ── POSITIONS (editable) ────────────────────────────────────────────────
st.subheader("Positions")

edit_rows = [{
    "name": f.get("name", ""),
    "year_invested": f.get("year_invested", 2024),
    "expected_exit_year": f.get("expected_exit_year") or 0,
    "committed_eur": _safe(f.get("committed_eur", 0)),
    "called_eur": _safe(f.get("called_eur", 0)),
    f"NAV ({latest_yr_str})": _safe(f.get("value_history", {}).get(latest_yr_str, f.get("current_nav_eur", 0))),
    "expected_irr_pct": _safe(f.get("expected_irr_pct", 0)),
    "access_layer": f.get("access_layer", "Direct"),
    "status": f.get("status", "Active"),
} for f in items]

pos_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(
    columns=["name", "year_invested", "expected_exit_year", "committed_eur",
             "called_eur", f"NAV ({latest_yr_str})", "expected_irr_pct", "access_layer", "status"])

pos_numeric = ["committed_eur", "called_eur", f"NAV ({latest_yr_str})", "expected_irr_pct"]
# Cast integer columns to str for TextColumn compatibility
if "expected_exit_year" in pos_df.columns:
    pos_df["expected_exit_year"] = pos_df["expected_exit_year"].astype(str)
if "year_invested" in pos_df.columns:
    pos_df["year_invested"] = pos_df["year_invested"].astype(str)
st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — add/remove funds, edit values</p>', unsafe_allow_html=True)
pos_df_orig = pos_df.copy()
pos_df = utils.inject_formulas_for_edit(pos_df, "funds_positions", pos_numeric)
edited_pos = st.data_editor(pos_df, use_container_width=True, hide_index=True, num_rows="dynamic",
    column_config={
        "access_layer": st.column_config.SelectboxColumn("Access", options=["Direct", "LA", "ECI"]),
        "status": st.column_config.SelectboxColumn("Status", options=["Active", "Closed"]),
        **{c: st.column_config.TextColumn(c) for c in pos_numeric},
        "expected_exit_year": st.column_config.TextColumn("Exit Year"),
        "year_invested": st.column_config.TextColumn("Year Invested"),
    }, key="fund_positions_editor")
edited_pos = utils.process_math_in_df(edited_pos, pos_numeric, editor_key="funds_positions")
utils.track_unsaved_changes("fund_pos", pos_df_orig, edited_pos)

if st.button("💾 Save Positions", type="primary", key="fund_save_pos"):
    deleted = utils.check_deleted_items(items, edited_pos, name_col="name")
    if not deleted:
        st.session_state["_pending_save_fund_pos"] = True
    else:
        st.session_state["_delete_confirm_fund_pos"] = deleted
    st.rerun()

save_result = utils.handle_save_with_delete_confirmation("fund_pos", [])
if save_result == "save":
    new_items = []
    for j, (_, row) in enumerate(edited_pos.iterrows()):
        if row.get("name"):
            orig = items[j] if j < len(items) else {}
            exit_yr = int(row.get("expected_exit_year", 0) or 0)
            new_items.append({
                "id": orig.get("id", utils.new_id()),
                "name": row["name"],
                "year_invested": int(row.get("year_invested", 2024) or 2024),
                "expected_exit_year": exit_yr if exit_yr > 2000 else None,
                "committed_eur": float(row.get("committed_eur", 0) or 0),
                "called_eur": float(row.get("called_eur", 0) or 0),
                "current_nav_eur": float(row.get(f"NAV ({latest_yr_str})", 0) or 0),
                "expected_irr_pct": float(row.get("expected_irr_pct", 0) or 0),
                "access_layer": row.get("access_layer", "Direct"),
                "status": row.get("status", "Active"),
                "notes": orig.get("notes", ""),
                "capital_call_schedule": orig.get("capital_call_schedule", []),
                "value_history": orig.get("value_history", {}),
                "distribution_history": orig.get("distribution_history", {}),
            })
    utils.save_json(utils.DATA_DIR / "funds.json", new_items)
    utils.clear_unsaved("fund_pos")
    st.success("Positions saved!")
    st.rerun()
elif save_result == "cancelled":
    st.rerun()

st.divider()

# ── CAPITAL CALLS — Planned % Grid ──────────────────────────────────────
st.subheader("Capital Calls — Planned % of Committed")
st.caption("Enter expected capital call as % of committed capital per year. Last column shows total called / committed.")

cc_years = list(range(earliest_yr, utils.CURRENT_YEAR + 6))
cc_yr_strs = [str(y) for y in cc_years]

pct_rows = []
pct_source_map = {yr: {} for yr in cc_yr_strs}
for idx, f in enumerate(items):
    committed = f.get("committed_eur", 0)
    yr_inv = f.get("year_invested", 2020)
    schedule_map = {cs["year"]: cs for cs in f.get("capital_call_schedule", [])}
    row = {"Fund": f.get("name", ""), "Committed": committed}
    total_pct = 0
    for yr_str in cc_yr_strs:
        yr = int(yr_str)
        if yr < yr_inv:
            row[yr_str] = None
        else:
            cs = schedule_map.get(yr, {})
            pct = cs.get("planned_pct", 0) or 0
            row[yr_str] = pct
            total_pct += pct
            if pct > 0:
                pct_source_map[yr_str][idx] = "input"
    row["Total %"] = total_pct
    pct_rows.append(row)

pct_df = pd.DataFrame(pct_rows)
pct_bg, pct_cell = utils.build_valuation_style_maps(pct_source_map)

pct_result = utils.render_editable_aggrid_table(
    pct_df, key="aggrid_fund_cc_pct", height=min(400, 80 + 35 * len(pct_rows)),
    editable_cols=cc_yr_strs, numeric_cols=cc_yr_strs + ["Committed", "Total %"],
    bg_style_map=pct_bg, cell_style_map=pct_cell,
    editor_key="fund_cc_pct",
)

st.divider()

# ── CAPITAL CALLS — Actual EUR Grid ─────────────────────────────────────
st.subheader("Capital Calls — Actual EUR")
st.caption("Enter actual capital called (EUR) per year-end. Yellow = user-entered.")

act_rows = []
act_source_map = {yr: {} for yr in cc_yr_strs}
for idx, f in enumerate(items):
    yr_inv = f.get("year_invested", 2020)
    schedule_map = {cs["year"]: cs for cs in f.get("capital_call_schedule", [])}
    row = {"Fund": f.get("name", ""), "Committed": f.get("committed_eur", 0)}
    for yr_str in cc_yr_strs:
        yr = int(yr_str)
        if yr < yr_inv:
            row[yr_str] = None
        else:
            cs = schedule_map.get(yr, {})
            actual = cs.get("actual_eur", 0) or 0
            row[yr_str] = actual
            if actual > 0:
                act_source_map[yr_str][idx] = "input"
    row["Total Called"] = sum(row.get(yr, 0) or 0 for yr in cc_yr_strs)
    act_rows.append(row)

act_df = pd.DataFrame(act_rows)
act_bg, act_cell = utils.build_valuation_style_maps(act_source_map)

act_result = utils.render_editable_aggrid_table(
    act_df, key="aggrid_fund_cc_actual", height=min(400, 80 + 35 * len(act_rows)),
    editable_cols=cc_yr_strs, numeric_cols=cc_yr_strs + ["Committed", "Total Called"],
    bg_style_map=act_bg, cell_style_map=act_cell,
    editor_key="fund_cc_actual",
)

if st.button("💾 Save Capital Calls", type="primary", key="fund_save_cc"):
    all_funds = utils.load_json(utils.DATA_DIR / "funds.json", [])
    edited_pct = pct_result.data if hasattr(pct_result, 'data') else pct_result
    edited_act = act_result.data if hasattr(act_result, 'data') else act_result
    for idx, f_name in enumerate([f.get("name") for f in items]):
        for fund in all_funds:
            if fund.get("name") == f_name:
                new_sched = []
                for yr_str in cc_yr_strs:
                    yr = int(yr_str)
                    try:
                        pct_val = float(edited_pct.iloc[idx].get(yr_str, 0) or 0)
                    except (ValueError, TypeError, IndexError):
                        pct_val = 0
                    try:
                        act_val = float(edited_act.iloc[idx].get(yr_str, 0) or 0)
                    except (ValueError, TypeError, IndexError):
                        act_val = 0
                    if pct_val > 0 or act_val > 0:
                        new_sched.append({"year": yr, "planned_pct": pct_val, "actual_eur": act_val})
                fund["capital_call_schedule"] = new_sched
                fund["called_eur"] = sum(s["actual_eur"] for s in new_sched if s["year"] <= utils.CURRENT_YEAR)
                break
    utils.save_json(utils.DATA_DIR / "funds.json", all_funds)
    st.success("Capital calls saved!")
    st.rerun()

st.divider()

# ── VALUATIONS ──────────────────────────────────────────────────────────
st.subheader("Valuations")
st.caption("🟡 Yellow = user-entered NAV. White = formula: V(N-1) × (1+IRR) + Capital Call(N). "
           "User-entered values apply across all scenarios.")

scenario = st.selectbox("Scenario", utils.SCENARIOS, index=2, key="fund_proj_scenario")
proj_years = 10
val_start = earliest_yr
val_end = utils.CURRENT_YEAR + proj_years
val_years = list(range(val_start, val_end + 1))
val_yr_strs = [str(y) for y in val_years]

mult = utils.get_scenario_multipliers("pe", scenario)
irr_mult = mult["irr"]

val_rows = []
val_source_map = {yr: {} for yr in val_yr_strs}

for idx, f in enumerate(active):
    irr = f.get("expected_irr_pct", 0) * irr_mult / 100
    yr_inv = f.get("year_invested", 2020)
    vh = f.get("value_history", {})
    schedule = {cs["year"]: cs.get("actual_eur", 0) for cs in f.get("capital_call_schedule", [])}

    row = {"Fund": f.get("name", ""), "IRR": f"{f.get('expected_irr_pct', 0) * irr_mult:.0f}%",
           "Exit": str(f.get("expected_exit_year") or "Open")}

    prev_val = _safe(f.get("current_nav_eur", 0))
    for yr in val_years:
        yr_str = str(yr)
        if yr < yr_inv:
            row[yr_str] = 0
            continue

        override = vh.get(yr_str)
        has_override = override is not None and override > 0

        if yr == yr_inv:
            val = override if has_override else (vh.get(yr_str, prev_val) or prev_val)
        elif has_override:
            val = override
            val_source_map[yr_str][idx] = "input"
        else:
            new_call = _safe(schedule.get(yr, 0))
            val = prev_val * (1 + irr) + new_call

        exit_yr = f.get("expected_exit_year")
        if exit_yr and yr > exit_yr:
            val = 0

        val = _safe(val)
        prev_val = val
        row[yr_str] = round(val)

        # Mark overrides as input for yellow coloring
        if has_override:
            val_source_map[yr_str][idx] = "input"

    val_rows.append(row)

# Total row
total_row = {"Fund": "TOTAL", "IRR": "", "Exit": ""}
for yr_str in val_yr_strs:
    total_row[yr_str] = sum(r.get(yr_str, 0) or 0 for r in val_rows)
val_rows.append(total_row)

val_df = pd.DataFrame(val_rows)
val_bg, val_cell = utils.build_valuation_style_maps(val_source_map)

val_result = utils.render_editable_aggrid_table(
    val_df, key="aggrid_fund_valuations", height=min(500, 80 + 35 * len(val_rows)),
    editable_cols=val_yr_strs, numeric_cols=val_yr_strs,
    highlight_total_row=True, bg_style_map=val_bg, cell_style_map=val_cell,
    editor_key="fund_valuations",
)

if st.button("💾 Save Valuations", type="primary", key="fund_save_val"):
    all_funds = utils.load_json(utils.DATA_DIR / "funds.json", [])
    edited_val = val_result.data if hasattr(val_result, 'data') else val_result
    for idx, f in enumerate(active):
        name = f.get("name", "")
        for fund in all_funds:
            if fund.get("name") == name:
                vh = fund.get("value_history", {})
                for yr_str in val_yr_strs:
                    try:
                        new_val = float(edited_val.iloc[idx].get(yr_str, 0) or 0)
                    except (ValueError, TypeError, IndexError):
                        new_val = 0
                    orig_val = float(val_df.iloc[idx].get(yr_str, 0) or 0)
                    if abs(new_val - orig_val) > 0.5:
                        if new_val > 0:
                            vh[yr_str] = new_val
                        else:
                            vh.pop(yr_str, None)
                fund["value_history"] = vh
                # Update current_nav to latest value
                for yr in reversed(val_years):
                    if vh.get(str(yr), 0) > 0:
                        fund["current_nav_eur"] = vh[str(yr)]
                        break
                break
    utils.save_json(utils.DATA_DIR / "funds.json", all_funds)
    st.success("Valuations saved!")
    st.rerun()

st.divider()

# ── DISTRIBUTIONS ────────────────────────────────────────────────────────
st.subheader("Distributions")
st.caption("Enter distribution received per fund per year-end. Positive = cash in, Negative = cash out. "
           "All entries are 🟡 yellow (user-input). These flow into Cash Flow.")

dist_years = list(range(earliest_yr, utils.CURRENT_YEAR + 6))
dist_yr_strs = [str(y) for y in dist_years]

dist_rows = []
dist_source_map = {yr: {} for yr in dist_yr_strs}
for idx, f in enumerate(items):
    dh = f.get("distribution_history", {})
    yr_inv = f.get("year_invested", 2020)
    row = {"Fund": f.get("name", "")}
    for yr_str in dist_yr_strs:
        yr = int(yr_str)
        if yr < yr_inv:
            row[yr_str] = None
        else:
            val = dh.get(yr_str, 0) or 0
            row[yr_str] = val
            if val != 0:
                dist_source_map[yr_str][idx] = "input"
    row["Total"] = sum(dh.get(yr, 0) or 0 for yr in dist_yr_strs)
    dist_rows.append(row)

# Total row
dist_total = {"Fund": "TOTAL"}
for yr_str in dist_yr_strs:
    dist_total[yr_str] = sum(r.get(yr_str, 0) or 0 for r in dist_rows)
dist_total["Total"] = sum(dist_total.get(yr, 0) or 0 for yr in dist_yr_strs)
dist_rows.append(dist_total)

dist_df = pd.DataFrame(dist_rows)
dist_bg, dist_cell = utils.build_valuation_style_maps(dist_source_map)

dist_result = utils.render_editable_aggrid_table(
    dist_df, key="aggrid_fund_distributions", height=min(400, 80 + 35 * len(dist_rows)),
    editable_cols=dist_yr_strs, numeric_cols=dist_yr_strs + ["Total"],
    highlight_total_row=True, bg_style_map=dist_bg, cell_style_map=dist_cell,
    editor_key="fund_distributions",
)

if st.button("💾 Save Distributions", type="primary", key="fund_save_dist"):
    all_funds = utils.load_json(utils.DATA_DIR / "funds.json", [])
    edited_dist = dist_result.data if hasattr(dist_result, 'data') else dist_result
    for idx, f_name in enumerate([f.get("name") for f in items]):
        for fund in all_funds:
            if fund.get("name") == f_name:
                dh = {}
                for yr_str in dist_yr_strs:
                    try:
                        val = float(edited_dist.iloc[idx].get(yr_str, 0) or 0)
                    except (ValueError, TypeError, IndexError):
                        val = 0
                    if val != 0:
                        dh[yr_str] = val
                fund["distribution_history"] = dh
                break
    utils.save_json(utils.DATA_DIR / "funds.json", all_funds)
    st.success("Distributions saved!")
    st.rerun()
