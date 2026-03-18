import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

utils.inject_bloomberg_css()
st.title("Portfolio Overview")

# ── Scenario selector (inline, compact) ──
cols = st.columns([4, 1])
with cols[1]:
    scenario = st.selectbox("Scenario", utils.SCENARIOS,
        index=utils.SCENARIOS.index(st.session_state.get("scenario", "Base")),
        key="scenario_selector", label_visibility="collapsed")
st.session_state.scenario = scenario

fx = utils.load_fx_rates()
assumptions = utils.load_assumptions()
hist_by_asset = utils.get_historical_totals_by_asset(fx)
hist_net_worth = {yr: sum(assets.values()) for yr, assets in hist_by_asset.items()}
proj_data = utils.get_portfolio_projection_v2(scenario, fx, assumptions, years=16)

# ── KPI TICKER BAR ──
last_ye = str(utils.CURRENT_YEAR - 1)
prev_ye = str(utils.CURRENT_YEAR - 2)
total_nw = sum(hist_by_asset.get(last_ye, {}).values())
prev_nw = sum(hist_by_asset.get(prev_ye, {}).values())
yoy_pct = ((total_nw / prev_nw - 1) * 100) if prev_nw > 0 else 0
cash_pos = hist_by_asset.get(last_ye, {}).get("Cash", 0)
ye_liquid = sum(hist_by_asset.get(last_ye, {}).get(ac, 0) for ac in utils.ASSET_CLASSES if ac in utils.LIQUID)
liquid_pct = (ye_liquid / total_nw * 100) if total_nw > 0 else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("NET WORTH", utils.fmt_eur(total_nw), f"{last_ye} YE")
k2.metric("YOY", f"{yoy_pct:+.1f}%", f"vs {prev_ye}")
k3.metric("CASH", utils.fmt_eur(cash_pos), f"{last_ye} YE")
k4.metric("LIQUID", f"{liquid_pct:.0f}%", f"of portfolio")

# ── YEAR-END STATUS ──
_ye_year = utils.CURRENT_YEAR - 1  # Most critical year to close
_completeness = utils.get_year_end_completeness(_ye_year)
_missing = _completeness["missing_items"]
_complete = _completeness["complete_count"]
_total = _completeness["total_count"]

if _total > 0:
    _status_cols = st.columns([1, 3])
    with _status_cols[0]:
        st.metric(f"YEAR-END {_ye_year}", f"{_complete}/{_total}", "complete")
    with _status_cols[1]:
        if not _missing:
            st.success(f"✅ All {_ye_year} year-end data complete")
        else:
            st.error(f"❌ {len(_missing)} items missing for {_ye_year} year-end close")
            with st.expander(f"View missing items", expanded=False):
                _grouped: dict[str, list] = {}
                for item in _missing:
                    ac = item["asset_class"]
                    _grouped.setdefault(ac, []).append(item)
                for ac, items in _grouped.items():
                    details = ", ".join(f"{i['name']} ({i['field']})" for i in items)
                    st.markdown(f"❌ **{ac}** → {details}")
else:
    st.warning("No year-end data found. Import data to get started.")

# ── ASSET VALUES GRID with sparklines ──
st.markdown(f'<h2 style="margin-top:8px">Asset Values</h2>', unsafe_allow_html=True)

grid_acs = [ac for ac in utils.ASSET_CLASSES]
last_updated_yr = utils.CURRENT_YEAR - 1
recent_hist_years = [last_updated_yr - 1, last_updated_yr]
future_start = utils.CURRENT_YEAR
next_5 = list(range(future_start, future_start + 5))
every_3_start = next_5[-1] + 3 if next_5 else future_start + 8
after_5 = list(range(every_3_start, 2041, 3))
show_years = recent_hist_years + next_5 + after_5
all_hist_years_int = sorted(int(y) for y in hist_by_asset.keys() if int(y) < recent_hist_years[0])

def _build_grid(years_list):
    rows = []
    for ac in grid_acs:
        row = {"Asset Class": ac}
        ac_proj = proj_data["by_asset"].get(ac, [])
        for yr in years_list:
            yr_str = str(yr)
            # For completed years, use historical data; for future, use projection
            if yr < utils.CURRENT_YEAR and yr_str in hist_by_asset:
                val = hist_by_asset[yr_str].get(ac, 0)
            elif yr in proj_data["years"]:
                idx = proj_data["years"].index(yr)
                val = ac_proj[idx] if idx < len(ac_proj) else 0
            else:
                val = hist_by_asset.get(yr_str, {}).get(ac, 0)
            row[yr_str] = round(val) if val and not (isinstance(val, float) and math.isnan(val)) else 0
        rows.append(row)
    t_row = {"Asset Class": "TOTAL"}
    for yr in years_list:
        yr_str = str(yr)
        if yr < utils.CURRENT_YEAR and yr_str in hist_by_asset:
            t_row[yr_str] = round(sum(hist_by_asset[yr_str].values()))
        elif yr in proj_data["years"]:
            idx = proj_data["years"].index(yr)
            total_val = proj_data["total"][idx]
            t_row[yr_str] = round(total_val) if total_val and not (isinstance(total_val, float) and math.isnan(total_val)) else 0
        else:
            hist_sum = sum(v for v in hist_by_asset.get(yr_str, {}).values() if v and not (isinstance(v, float) and math.isnan(v)))
            t_row[yr_str] = round(hist_sum)
    rows.append(t_row)
    return rows, t_row

grid_rows, total_row = _build_grid(show_years)
grid_df = pd.DataFrame(grid_rows)
year_str_cols = [str(yr) for yr in show_years]

# Allocation deviation coloring
inv_plan = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
if not isinstance(inv_plan, dict): inv_plan = {}
target_alloc = inv_plan.get("target_allocation", {})
bg_style_map = {}
for yr in show_years:
    if yr < utils.CURRENT_YEAR:
        continue
    yr_str = str(yr)
    yr_total = total_row.get(yr_str, 0)
    if yr_total <= 0:
        continue
    col_bg = {}
    for row_idx, ac in enumerate(grid_acs):
        ideal_pct = target_alloc.get(ac, 0)
        if ideal_pct <= 0:
            continue
        ac_val = grid_rows[row_idx].get(yr_str, 0)
        actual_pct = (ac_val / yr_total * 100) if yr_total > 0 else 0
        deviation = (actual_pct - ideal_pct) / ideal_pct if ideal_pct > 0 else 0
        if deviation > 0.2:
            col_bg[row_idx] = "#3a1111"
        elif deviation < -0.2:
            col_bg[row_idx] = "#0a2a0a"
    if col_bg:
        bg_style_map[yr_str] = col_bg

utils.render_aggrid_table(grid_df, key="aggrid_overview_asset_year_grid",
                          height=min(340, max(200, len(grid_rows) * 28 + 36)),
                          numeric_cols=year_str_cols,
                          highlight_total_row=True,
                          bg_style_map=bg_style_map)

if all_hist_years_int:
    show_hist = st.checkbox(f"Show {all_hist_years_int[0]}–{all_hist_years_int[-1]}",
                            value=False, key="show_hist_years")
    if show_hist:
        hist_rows, _ = _build_grid(all_hist_years_int)
        utils.render_aggrid_table(pd.DataFrame(hist_rows), key="aggrid_overview_hist_years",
                                  height=min(340, max(200, len(hist_rows) * 28 + 36)),
                                  numeric_cols=[str(yr) for yr in all_hist_years_int],
                                  highlight_total_row=True)

# ── COMPACT PROJECTION STRIP ──
st.markdown(f'<h2>Projection ({scenario})</h2>', unsafe_allow_html=True)

# Compact: show key milestones inline + small chart
def _proj_val(proj, yr):
    if yr in proj["years"]:
        v = proj["total"][proj["years"].index(yr)]
        if v and not (isinstance(v, float) and math.isnan(v)):
            return v
    return 0

p_now = _proj_val(proj_data, utils.CURRENT_YEAR)
p_5yr = _proj_val(proj_data, utils.CURRENT_YEAR + 5)
p_10yr = _proj_val(proj_data, utils.CURRENT_YEAR + 10)
p_15yr = _proj_val(proj_data, min(utils.CURRENT_YEAR + 15, proj_data["years"][-1]))

m1, m2, m3, m4 = st.columns(4)
m1.metric("NOW", utils.fmt_eur(p_now), str(utils.CURRENT_YEAR))
m2.metric("5 YR", utils.fmt_eur(p_5yr), f"{((p_5yr/p_now-1)*100):+.0f}%" if p_now > 0 else "")
m3.metric("10 YR", utils.fmt_eur(p_10yr), f"{((p_10yr/p_now-1)*100):+.0f}%" if p_now > 0 else "")
m4.metric("15 YR", utils.fmt_eur(p_15yr), f"{((p_15yr/p_now-1)*100):+.0f}%" if p_now > 0 else "")

# Compact projection chart
colors = {"Super Bear": utils.C_RED, "Bear": "#ff9944", "Base": utils.C_ORANGE, "Bull": utils.C_GREEN}
fig = go.Figure()

# Historical
if hist_net_worth:
    hist_years_sorted = sorted(int(y) for y in hist_net_worth.keys() if hist_net_worth[y] > 0)
    if hist_years_sorted:
        fig.add_trace(go.Scatter(
            x=hist_years_sorted, y=[hist_net_worth[str(y)] for y in hist_years_sorted],
            mode="lines+markers", name="Historical",
            line=dict(color="#555", dash="dot", width=1.5), marker=dict(size=3),
            hovertemplate="%{x}: €%{y:,.0f}<extra>Historical</extra>"))

# Scenario lines
selected_scenarios = ["Base", "Bull", "Bear"]
for s in selected_scenarios:
    s_proj = utils.get_portfolio_projection_v2(s, fx, assumptions, years=16)
    lw = 2.5 if s == scenario else 1
    dash = None if s == scenario else "dash"
    fig.add_trace(go.Scatter(
        x=s_proj["years"], y=s_proj["total"], mode="lines",
        name=s, line=dict(color=colors.get(s, "#fff"), width=lw, dash=dash),
        hovertemplate="%{x}: €%{y:,.0f}<extra>" + s + "</extra>"))

fig.update_layout(**utils.bloomberg_chart_layout(height=250))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── ALLOCATION (compact side-by-side) ──
col_alloc, col_liq, col_returns = st.columns([2, 1, 2])

with col_alloc:
    st.markdown(f'<h2>Allocation ({last_ye})</h2>', unsafe_allow_html=True)
    ye_values = hist_by_asset.get(last_ye, {})
    for ac in utils.ASSET_CLASSES:
        if ac not in ye_values or ye_values[ac] <= 0:
            if utils.CURRENT_YEAR - 1 in proj_data["years"]:
                idx = proj_data["years"].index(utils.CURRENT_YEAR - 1)
                ac_proj = proj_data["by_asset"].get(ac, [])
                ye_values[ac] = ac_proj[idx] if idx < len(ac_proj) else 0

    pos_ye = {k: v for k, v in ye_values.items() if v > 0 and k != "Debt" and k in utils.ASSET_CLASSES}
    if pos_ye:
        fig2 = px.pie(
            names=list(pos_ye.keys()), values=list(pos_ye.values()),
            hole=0.5,
            color_discrete_sequence=[utils.C_ORANGE, utils.C_GREEN, "#8b5cf6", "#f59e0b",
                                     "#eab308", "#ec4899", "#f97316", "#6366f1"]
        )
        fig2.update_layout(**utils.bloomberg_chart_layout(height=220, margin=dict(t=5,b=5,l=5,r=5),
                           showlegend=True, legend=dict(font=dict(size=9), x=1.05, y=0.5, orientation="v")))
        fig2.update_traces(textposition='inside', textinfo='percent', textfont_size=9)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

with col_liq:
    st.markdown(f'<h2>Liquidity</h2>', unsafe_allow_html=True)
    ye_liq = sum(ye_values.get(ac, 0) for ac in utils.ASSET_CLASSES if ac in utils.LIQUID)
    ye_illiq = sum(ye_values.get(ac, 0) for ac in utils.ASSET_CLASSES if ac in utils.ILLIQUID)
    liq_data = {"Liq": max(0, ye_liq), "Illiq": max(0, ye_illiq)}
    if any(v > 0 for v in liq_data.values()):
        fig3 = px.pie(
            names=list(liq_data.keys()), values=list(liq_data.values()),
            hole=0.5, color_discrete_map={"Liq": utils.C_GREEN, "Illiq": "#8b5cf6"}
        )
        fig3.update_layout(**utils.bloomberg_chart_layout(height=220, margin=dict(t=5,b=5,l=5,r=5),
                           showlegend=False))
        fig3.update_traces(textposition='inside', textinfo='percent+label', textfont_size=10)
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

with col_returns:
    st.markdown(f'<h2>Investment Returns</h2>', unsafe_allow_html=True)
    valid_hist = {y: v for y, v in hist_net_worth.items() if v > 0}
    if len(valid_hist) > 1:
        hist_years_sorted = sorted(int(y) for y in valid_hist.keys())
        hist_vals = [valid_hist[str(y)] for y in hist_years_sorted]
        cf_data = utils.load_json(utils.DATA_DIR / "cashflow.json", {})
        income_data = cf_data.get("income", {})
        real_growth = [0]
        for i in range(1, len(hist_vals)):
            if hist_vals[i-1] > 0:
                emp_inc = income_data.get("Salary", {}).get(str(hist_years_sorted[i]), 0) + \
                          income_data.get("Optiver Bonus", {}).get(str(hist_years_sorted[i]), 0)
                real_growth.append(((hist_vals[i] - hist_vals[i-1] - emp_inc) / hist_vals[i-1]) * 100)
            else:
                real_growth.append(0)

        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            x=hist_years_sorted, y=real_growth,
            marker_color=[utils.C_GREEN if v >= 0 else utils.C_RED for v in real_growth],
            text=[f"{v:+.0f}%" for v in real_growth], textposition="outside",
            textfont=dict(size=9),
        ))
        fig4.update_layout(**utils.bloomberg_chart_layout(height=220, showlegend=False,
                           yaxis=dict(gridcolor=utils.GRID_LINE, tickformat=".0f",
                                      tickfont=dict(size=9), title=None)))
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

# ── EXPANDERS (details) ──
with st.expander("Projection Breakdown"):
    def _idx(yr):
        return proj_data["years"].index(yr) if yr in proj_data["years"] else 0
    idx_now = _idx(utils.CURRENT_YEAR)
    idx_5yr = _idx(min(utils.CURRENT_YEAR + 5, proj_data["years"][-1]))
    idx_10yr = min(len(proj_data["total"]) - 1, _idx(min(utils.CURRENT_YEAR + 10, proj_data["years"][-1])))
    proj_rows = []
    for ac in utils.ASSET_CLASSES:
        ac_proj = proj_data["by_asset"].get(ac, [0] * len(proj_data["years"]))
        current = ac_proj[idx_now] if idx_now < len(ac_proj) else 0
        yr5 = ac_proj[idx_5yr] if idx_5yr < len(ac_proj) else current
        yr10 = ac_proj[idx_10yr] if idx_10yr < len(ac_proj) else current
        proj_rows.append({
            "Asset Class": ac,
            f"{utils.CURRENT_YEAR}": utils.fmt_eur_short(current),
            "5yr": utils.fmt_eur_short(yr5),
            "10yr": utils.fmt_eur_short(yr10),
            "Growth": f"{((yr10/current - 1)*100):+.0f}%" if current and current > 0 else "N/A",
        })
    t_current = proj_data["total"][idx_now]
    t_5yr = proj_data["total"][idx_5yr]
    t_10yr = proj_data["total"][idx_10yr]
    proj_rows.append({
        "Asset Class": "TOTAL",
        f"{utils.CURRENT_YEAR}": utils.fmt_eur_short(t_current),
        "5yr": utils.fmt_eur_short(t_5yr), "10yr": utils.fmt_eur_short(t_10yr),
        "Growth": f"{((t_10yr/t_current - 1)*100):+.0f}%" if t_current > 0 else "N/A",
    })
    utils.render_aggrid_table(pd.DataFrame(proj_rows), key="aggrid_overview_projections",
                              height=min(340, max(200, len(proj_rows) * 28 + 36)))

with st.expander("PE Projection Detail (IRR × Prob)"):
    pe_items = utils.load_json(utils.DATA_DIR / "private_equity.json", [])
    pe_rows = []
    for item in pe_items:
        if item.get("status") != "Active" or item.get("type") == "Real Estate":
            continue
        current = item.get("current_value_eur", 0)
        irr = item.get("expected_irr_pct", 0)
        prob = item.get("success_probability_pct", 100)
        ev_5yr = current * (1 + irr / 100) ** 5 * (prob / 100)
        ev_10yr = current * (1 + irr / 100) ** 10 * (prob / 100)
        pe_rows.append({
            "Name": item.get("name", ""),
            "Current": utils.fmt_eur_short(current),
            "IRR": f"{irr}%", "Prob": f"{prob}%",
            "EV 5yr": utils.fmt_eur_short(ev_5yr),
            "EV 10yr": utils.fmt_eur_short(ev_10yr),
        })
    if pe_rows:
        utils.render_aggrid_table(pd.DataFrame(pe_rows), key="aggrid_overview_pe_detail",
                                  height=min(340, max(200, len(pe_rows) * 28 + 36)))

with st.expander("Edit Historical Asset Values"):
    asset_hist = utils.load_json(utils.DATA_DIR / "asset_history.json", {})
    all_hist_years = set(str(y) for y in range(2018, utils.CURRENT_YEAR + 1))
    for ac_data in asset_hist.values():
        if isinstance(ac_data, dict):
            all_hist_years.update(ac_data.keys())
    sorted_years = sorted(all_hist_years)
    editable_acs = [ac for ac in utils.ASSET_CLASSES if ac not in ("Private Equity", "Real Estate")]
    edit_rows = []
    for yr in sorted_years:
        row = {"Year": int(yr)}
        for ac in editable_acs:
            row[ac] = asset_hist.get(ac, {}).get(yr, 0)
        row["PE (auto)"] = utils.get_pe_value_by_year(int(yr))
        row["RE (auto)"] = utils.get_re_value_by_year(int(yr))
        row["Total"] = row["PE (auto)"] + row["RE (auto)"] + sum(row.get(ac, 0) for ac in editable_acs)
        edit_rows.append(row)
    edit_df = pd.DataFrame(edit_rows)
    col_config = {ac: st.column_config.NumberColumn(format="€%.0f") for ac in editable_acs}
    col_config["PE (auto)"] = st.column_config.NumberColumn(format="€%.0f")
    col_config["RE (auto)"] = st.column_config.NumberColumn(format="€%.0f")
    col_config["Total"] = st.column_config.NumberColumn(format="€%.0f")
    edited_hist = st.data_editor(
        edit_df, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config=col_config, disabled=["PE (auto)", "RE (auto)", "Total"])
    edited_hist = utils.process_math_in_df(edited_hist, editable_acs, editor_key="overview_targets")
    if st.button("Save Historical Values", type="primary"):
        new_asset_hist = {ac: {} for ac in editable_acs}
        for _, row in edited_hist.iterrows():
            yr_str = str(int(row["Year"]))
            for ac in editable_acs:
                new_asset_hist[ac][yr_str] = float(row.get(ac, 0) or 0)
        utils.save_json(utils.DATA_DIR / "asset_history.json", new_asset_hist)
        st.success("Saved!")
        st.rerun()
