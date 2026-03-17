import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("🏠 Real Estate")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)

items = utils.load_json(utils.DATA_DIR / "real_estate.json", [])

active = [i for i in items if i.get("status") == "Active"]
exited = [i for i in items if i.get("status") == "Exited"]

total_invested = sum(i.get("amount_invested_eur", 0) for i in items)
total_exit_proceeds = sum(i.get("exit_value_eur", 0) for i in exited)
total_rental = sum(i.get("annual_rental_eur", 0) for i in active)
total_mortgage = sum(i.get("mortgage_outstanding_eur", 0) for i in active)

# Year-end value: use compute_re_timeline for latest completed year (same as Overview)
latest_yr_int = utils.CURRENT_YEAR - 1
re_val_latest = utils.compute_re_timeline([latest_yr_int], "Base")
total_current = re_val_latest[0] if re_val_latest else 0
year_label = f" ({latest_yr_int} YE)"
net_equity = total_current - total_mortgage

# Check if any items are missing year-end values for latest year
val_items = utils._get_re_valuation_items()
missing_items = []
for p in val_items:
    status = p.get("status", "Active")
    exit_yr = p.get("expected_exit_year", 9999)
    yr_invested = p.get("year_invested", 9999)
    if latest_yr_int < yr_invested:
        continue
    if status == "Exited" and latest_yr_int >= exit_yr:
        continue
    vh = p.get("value_history", {})
    if str(latest_yr_int) not in vh:
        missing_items.append(p.get("name", "Unknown"))
missing_note = ""
if missing_items:
    missing_note = f' <span style="color:red">* {len(missing_items)} items without {latest_yr_int} valuation</span>'

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"Active Value{year_label}", utils.fmt_eur(total_current))
c2.metric("Total Invested", utils.fmt_eur(total_invested))
c3.metric("Net Equity", utils.fmt_eur(net_equity))
c4.metric("Annual Rent", utils.fmt_eur(total_rental))
c5.metric("Exit Proceeds", utils.fmt_eur(total_exit_proceeds))
if missing_note:
    st.markdown(missing_note, unsafe_allow_html=True)

st.divider()

# --- Positions Section ---
st.subheader(f"Properties ({len(items)})")
edit_rows = [{
    "name": p.get("name", ""),
    "year_invested": p.get("year_invested", 2020),
    "amount_invested_eur": p.get("amount_invested_eur", 0),
    "current_value_eur": p.get("current_value_eur", 0),
    "exit_value_eur": p.get("exit_value_eur", 0),
    "annual_rental_eur": p.get("annual_rental_eur", 0),
    "mortgage_total_eur": p.get("mortgage_total_eur", 0),
    "mortgage_outstanding_eur": p.get("mortgage_outstanding_eur", 0),
    "expected_irr_pct": p.get("expected_irr_pct", 0),
    "success_probability_pct": p.get("success_probability_pct", 100),
    "expected_exit_year": p.get("expected_exit_year", 3000),
    "status": p.get("status", "Active"),
    "notes": p.get("notes", ""),
} for p in items]

edit_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(
    columns=["name", "year_invested", "amount_invested_eur", "current_value_eur",
             "exit_value_eur", "annual_rental_eur", "mortgage_total_eur",
             "mortgage_outstanding_eur", "expected_irr_pct", "success_probability_pct",
             "expected_exit_year", "status", "notes"])

row_height = min(500, max(250, len(edit_rows) * 32 + 40))
st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — add/edit properties directly. Add rows at the bottom.</p>', unsafe_allow_html=True)
st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
edited = st.data_editor(edit_df, use_container_width=True, hide_index=True, num_rows="dynamic",
    height=row_height,
    column_config={
        "status": st.column_config.SelectboxColumn("Status", options=["Active", "Exited"]),
        "amount_invested_eur": st.column_config.NumberColumn("Invested", format="€%.0f"),
        "current_value_eur": st.column_config.NumberColumn("Current Value", format="€%.0f"),
        "exit_value_eur": st.column_config.NumberColumn("Exit Value", format="€%.0f"),
        "annual_rental_eur": st.column_config.NumberColumn("Rent/yr", format="€%.0f"),
        "mortgage_total_eur": st.column_config.NumberColumn("Mortgage Total", format="€%.0f"),
        "mortgage_outstanding_eur": st.column_config.NumberColumn("Mortgage Out.", format="€%.0f"),
        "expected_irr_pct": st.column_config.NumberColumn("IRR %", format="%.1f%%"),
        "success_probability_pct": st.column_config.NumberColumn("Prob %", format="%.0f%%"),
    })
edited = utils.process_math_in_df(edited, ["amount_invested_eur", "current_value_eur", "exit_value_eur",
                                             "annual_rental_eur", "mortgage_total_eur", "mortgage_outstanding_eur",
                                             "expected_irr_pct", "success_probability_pct"], editor_key="real_estate_properties")

if st.button("💾 Save Properties", type="primary", key="re_save"):
    new_items = []
    for j, (_, row) in enumerate(edited.iterrows()):
        if row.get("name"):
            orig = items[j] if j < len(items) else {}
            new_items.append({
                "id": orig.get("id", utils.new_id()),
                "name": row["name"],
                "year_invested": int(row.get("year_invested", 2020) or 2020),
                "amount_invested_eur": float(row.get("amount_invested_eur", 0) or 0),
                "current_value_eur": float(row.get("current_value_eur", 0) or 0),
                "exit_value_eur": float(row.get("exit_value_eur", 0) or 0),
                "annual_rental_eur": float(row.get("annual_rental_eur", 0) or 0),
                "mortgage_total_eur": float(row.get("mortgage_total_eur", 0) or 0),
                "mortgage_outstanding_eur": float(row.get("mortgage_outstanding_eur", 0) or 0),
                "expected_irr_pct": float(row.get("expected_irr_pct", 0) or 0),
                "success_probability_pct": float(row.get("success_probability_pct", 100) or 100),
                "expected_exit_year": int(row.get("expected_exit_year", 3000) or 3000),
                "status": row.get("status", "Active"),
                "notes": row.get("notes", ""),
                "value_history": orig.get("value_history", {}),
            })
    utils.save_json(utils.DATA_DIR / "real_estate.json", new_items)
    st.success("Saved!")
    st.rerun()

# --- Exited Positions ---
if exited:
    st.subheader(f"Exited ({len(exited)})")
    exit_rows = []
    for p in exited:
        exit_val = p.get("exit_value_eur", 0)
        invested = p.get("amount_invested_eur", 0)
        pnl = exit_val - invested
        exit_rows.append({
            "Name": p.get("name", ""),
            "Year In": p.get("year_invested", ""),
            "Year Out": p.get("expected_exit_year", ""),
            "Invested": utils.fmt_eur_short(invested),
            "Exit Value": utils.fmt_eur_short(exit_val),
            "P&L": utils.fmt_eur_short(pnl),
            "MOIC": f"{exit_val / invested:.2f}x" if invested > 0 else "0x",
            "Notes": p.get("notes", ""),
        })
    df_exited = pd.DataFrame(exit_rows)
    row_height = min(400, max(200, len(exit_rows) * 32 + 40))
    utils.render_aggrid_table(df_exited, key="aggrid_re_exited", height=row_height)

# --- Portfolio Value Over Time Chart ---
st.subheader("Portfolio Value Over Time")
all_years_chart = set()
for p in items:
    vh = p.get("value_history", {})
    if vh:
        all_years_chart.update(int(y) for y in vh.keys())
    yr = p.get("year_invested", utils.CURRENT_YEAR)
    all_years_chart.add(yr)
all_years_chart.add(utils.CURRENT_YEAR)
sorted_years_chart = sorted(all_years_chart)

year_totals = {y: 0 for y in sorted_years_chart}
for p in items:
    vh = p.get("value_history", {})
    status = p.get("status", "Active")
    exit_yr = p.get("expected_exit_year", 9999)
    for y in sorted_years_chart:
        if status == "Exited" and y >= exit_yr:
            continue
        val = vh.get(str(y), 0)
        if not vh and status == "Active":
            if y >= p.get("year_invested", 9999):
                val = p.get("current_value_eur", 0)
        year_totals[y] += val

if any(v > 0 for v in year_totals.values()):
    fig_total = go.Figure()
    fig_total.add_trace(go.Scatter(
        x=sorted_years_chart,
        y=[year_totals[y] for y in sorted_years_chart],
        mode="lines+markers",
        line=dict(color="#44ff88", width=3),
        marker=dict(size=6),
        name="Total RE Value",
        text=[utils.fmt_eur(year_totals[y]) for y in sorted_years_chart],
        hovertemplate="%{x}: %{text}",
    ))
    fig_total.update_layout(
        template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
        xaxis_title="Year", yaxis_title="Value (EUR)",
        yaxis=dict(tickformat=",.0f"), hovermode="x unified",
    )
    st.plotly_chart(fig_total, use_container_width=True)

st.divider()

# --- Valuations Section ---
st.subheader("Valuations (IRR × Probability)")

scenario = st.selectbox("Scenario", utils.SCENARIOS, index=2, key="re_proj_scenario")

# All relevant items: Active + Exited (until exit year)
val_items = utils._get_re_valuation_items()

# Build full timeline: from earliest investment year through current+10
earliest_year = min((p.get("year_invested", utils.CURRENT_YEAR) for p in val_items), default=utils.CURRENT_YEAR)
earliest_year = min(earliest_year, 2020)  # At least 2020
proj_years = 10
years_list = list(range(earliest_year, utils.CURRENT_YEAR + proj_years + 1))

mult = utils.get_scenario_multipliers("re", scenario)

proj_rows = []
totals_by_year = [0.0] * len(years_list)
is_actual_map = {}  # (row_idx, yr_str) -> bool

for row_idx, p in enumerate(val_items):
    status = p.get("status", "Active")
    exit_yr = p.get("expected_exit_year", 9999)
    current = p.get("current_value_eur", 0)
    year_invested = p.get("year_invested", 2000)
    irr = p.get("expected_irr_pct", 0) * mult["irr"]
    prob = min(100, p.get("success_probability_pct", 100) * mult["prob"])
    name_label = p.get("name", "")
    if status == "Exited":
        name_label += f" (exited {exit_yr})"
    row = {"Name": name_label, "Current": round(current),
           "IRR": f"{irr:.0f}%", "Prob": f"{prob:.0f}%",
           "Year In": year_invested}
    vh = p.get("value_history", {})
    prev_val = 0
    for i, yr in enumerate(years_list):
        if yr < year_invested:
            row[str(yr)] = 0
            is_actual_map[(row_idx, str(yr))] = False
            continue
        if status == "Exited" and yr >= exit_yr:
            row[str(yr)] = 0
            is_actual_map[(row_idx, str(yr))] = False
            continue

        is_input = False
        override = vh.get(str(yr))
        has_override = override is not None and override > 0

        if has_override:
            val = override
            is_input = True
        elif prev_val == 0:
            val = vh.get(str(yr), 0)
            if val <= 0:
                val = current if current > 0 else 0
        else:
            if status == "Exited":
                val = prev_val
            else:
                val = prev_val * (1 + irr / 100) * (prob / 100) if prob > 0 else 0

        prev_val = val
        row[str(yr)] = round(val)
        totals_by_year[i] += val
        is_actual_map[(row_idx, str(yr))] = is_input
    proj_rows.append(row)

# Total row
total_row = {"Name": "TOTAL", "Current": 0, "IRR": "", "Prob": "", "Year In": 0}
for i, yr in enumerate(years_list):
    total_row[str(yr)] = round(totals_by_year[i])
proj_rows.append(total_row)

proj_df = pd.DataFrame(proj_rows)
orig_df = proj_df.copy()
year_strs = [str(yr) for yr in years_list]

row_height = min(500, max(250, len(proj_rows) * 32 + 40))

# Build per-cell coloring from is_actual_map
col_source_map = {}
for yr_str in year_strs:
    yr_sources = {}
    for row_idx in range(len(val_items)):  # Exclude TOTAL row
        if is_actual_map.get((row_idx, yr_str), False):
            yr_sources[row_idx] = "input"
    if yr_sources:
        col_source_map[yr_str] = yr_sources

bg_style_map, cell_style_map = utils.build_valuation_style_maps(col_source_map)
formula_map = utils.get_formula_map("real_estate_valuations", len(proj_df), year_strs)

st.caption("🟡 Yellow = user-entered actual. Default = formula. Double-click to edit.")

grid_result = utils.render_editable_aggrid_table(
    proj_df, key="re_valuation_aggrid",
    editable_cols=year_strs,
    numeric_cols=["Current"] + year_strs,
    bg_style_map=bg_style_map, cell_style_map=cell_style_map,
    formula_map=formula_map, editor_key="real_estate_valuations",
    highlight_total_row=True,
    height=row_height,
)
edited_proj = grid_result.data
edited_proj = utils.process_math_in_df(edited_proj, year_strs, editor_key="real_estate_valuations")

if st.button("💾 Save Valuations", type="primary", key="re_save_valuations"):
    all_re = utils.load_json(utils.DATA_DIR / "real_estate.json", [])
    for row_idx, p in enumerate(val_items):
        name = p.get("name", "")
        for item in all_re:
            if item.get("name") == name:
                vh = item.get("value_history", {})
                for yr_str in year_strs:
                    new_val = float(edited_proj.iloc[row_idx].get(yr_str, 0) or 0)
                    orig_val = float(orig_df.iloc[row_idx].get(yr_str, 0) or 0)
                    if abs(new_val - orig_val) > 0.5:  # Cell was edited
                        if new_val > 0:
                            vh[yr_str] = new_val
                        else:
                            vh.pop(yr_str, None)
                item["value_history"] = vh
                for yr in reversed(years_list):
                    if vh.get(str(yr), 0) > 0:
                        item["current_value_eur"] = vh[str(yr)]
                        break
                if item.get("status") == "Exited":
                    for yr in reversed(years_list):
                        if vh.get(str(yr), 0) > 0:
                            item["exit_value_eur"] = vh[str(yr)]
                            break
                break
    utils.save_json(utils.DATA_DIR / "real_estate.json", all_re)
    st.success("Valuations saved! Projections will update.")
    st.rerun()

# Data source info
with st.expander("ℹ️ Data Sources"):
    st.markdown("""
**Year-end values**
- 🟡 **Actual**: User-entered values stored as anchors in value_history. These override formula projections.
- ⚪ **Formula**: `V(N) = V(N-1) × (1 + IRR%) × (Probability%)`
- Edit any year cell to set an actual value. Set to 0 to remove an override.

**IRR & Probability**
- Per-item IRR from 🏠 RE > Positions tab
- Scenario multipliers from ⚙️ FX & Settings > IRR-Based Asset Scenarios
- Current scenario: **{}** (IRR ×{:.2f}, Prob ×{:.2f})

**Actuals in this table:**
""".format(scenario, mult["irr"], mult["prob"]))
    actual_summary = []
    for row_idx, p in enumerate(val_items):
        vh = p.get("value_history", {})
        actual_yrs = [yr for yr in sorted(vh.keys()) if vh[yr] > 0]
        if actual_yrs:
            actual_summary.append(f"- **{p.get('name', '')}**: {', '.join(actual_yrs)}")
    if actual_summary:
        st.markdown("\n".join(actual_summary))
    else:
        st.markdown("_No actual values entered yet._")

# Chart
fig_proj = go.Figure()
actual_x, actual_y, proj_x, proj_y = [], [], [], []
for i, yr in enumerate(years_list):
    if yr <= utils.CURRENT_YEAR and totals_by_year[i] > 0:
        actual_x.append(yr)
        actual_y.append(totals_by_year[i])
    elif totals_by_year[i] > 0:
        proj_x.append(yr)
        proj_y.append(totals_by_year[i])
if actual_x:
    fig_proj.add_trace(go.Scatter(x=actual_x, y=actual_y, mode="lines+markers",
                                   line=dict(color="#f59e0b", width=3), name="Actual",
                                   text=[utils.fmt_eur(v) for v in actual_y],
                                   hovertemplate="%{x}: %{text}"))
if proj_x:
    fig_proj.add_trace(go.Scatter(x=proj_x, y=proj_y, mode="lines+markers",
                                   line=dict(color="#60a5fa", width=2, dash="dot"), name="Projected",
                                   text=[utils.fmt_eur(v) for v in proj_y],
                                   hovertemplate="%{x}: %{text}"))
fig_proj.update_layout(
    template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
    xaxis_title="Year", yaxis_title="Value (EUR)",
    yaxis=dict(tickformat=",.0f"), title=f"RE Valuation ({scenario})",
)
st.plotly_chart(fig_proj, use_container_width=True)
