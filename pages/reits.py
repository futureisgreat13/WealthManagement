import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("🏢 REITs")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)
utils.render_year_end_alert("REITs")

positions = utils.load_json(utils.DATA_DIR / "public_stocks.json", [])
reits = [p for p in positions if p.get("type") == "REIT"]

# --- Metrics ---
avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
reits_hist = avh.get("REITs", {})
all_ibkr_years = sorted(reits_hist.keys())

if all_ibkr_years:
    latest_yr = all_ibkr_years[-1]
    total_val = reits_hist.get(latest_yr, 0)
    year_label = f" ({latest_yr} YE)"
else:
    total_val = sum(p.get("value_eur", 0) for p in reits)
    year_label = ""

total_cost = sum(p.get("cost_eur", 0) for p in reits)
total_pnl = total_val - total_cost
total_div = sum(p.get("net_div_eur", 0) for p in reits)
div_yield = (total_div / total_val * 100) if total_val > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"Total Value{year_label}", utils.fmt_eur(total_val))
c2.metric("Total Cost", utils.fmt_eur(total_cost))
c3.metric("Total P&L", utils.fmt_eur(total_pnl))
c4.metric("Annual Dividends", utils.fmt_eur(total_div))
c5.metric("Avg Yield", f"{div_yield:.1f}%")

st.divider()

tab1, tab2 = st.tabs(["Positions", "Valuations"])

with tab1:
    if not reits:
        st.info("No REIT positions yet.")
    else:
        rows = []
        for p in reits:
            val = p.get("value_eur", 0)
            div = p.get("net_div_eur", 0)
            rows.append({
                "Ticker": p.get("ticker", ""),
                "Name": p.get("name", ""),
                "Ccy": p.get("currency", ""),
                "Qty": p.get("quantity", 0),
                "Cost (EUR)": utils.fmt_eur_short(p.get("cost_eur", 0)),
                "Value (EUR)": utils.fmt_eur_short(val),
                "P&L (EUR)": utils.fmt_eur_short(val - p.get("cost_eur", 0)),
                "Return %": f"{p.get('return_pct', 0):+.1f}%",
                "Div/yr": utils.fmt_eur_short(div),
                "Yield %": f"{div / val * 100:.1f}%" if val > 0 else "0%",
            })
        df = pd.DataFrame(rows)
        utils.render_aggrid_table(df, key="aggrid_reits_positions", height=min(400, max(200, len(rows) * 32 + 40)))

with tab2:
    st.subheader("Valuations — Historical & Projected")

    avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
    reit_history = avh.get("REITs", {})

    scenario = st.selectbox("Scenario", utils.SCENARIOS, index=2, key="reit_proj_scenario")
    assumptions = utils.load_assumptions()
    return_pct = utils.get_return_pct("REITs", scenario, assumptions)
    st.info(f"Expected return: {return_pct:.1f}% — set in ⚙️ FX & Settings > Liquid Asset Scenario Returns")

    plan = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
    planned_reit = plan.get("planned_investment_yr", {}).get("REITs", 0)

    def get_new_capital(yr):
        return utils.get_valuation_new_capital("REITs", "REIT", yr)

    hist_years = sorted([int(y) for y in reit_history.keys() if reit_history[y] > 0])
    start_year = min(hist_years) if hist_years else 2020
    end_year = max(utils.CURRENT_YEAR + 9, max(hist_years) + 5 if hist_years else 2034)
    all_years = list(range(start_year, end_year + 1))

    values = utils.compute_liquid_timeline("REITs", all_years, scenario)
    value_is_actual = []
    for yr in all_years:
        actual = reit_history.get(str(yr))
        value_is_actual.append(actual is not None and actual > 0)

    rows = []
    for i, yr in enumerate(all_years):
        rows.append({
            "Year": yr,
            "Value (EUR)": round(values[i]),
            "New Capital": round(get_new_capital(yr)),
        })

    proj_df = pd.DataFrame(rows)
    orig_df = proj_df.copy()

    # Build per-cell coloring
    col_source_map = {"Value (EUR)": {}, "New Capital": {}}
    stored_formulas = utils.load_json(utils.DATA_DIR / "formulas.json", {})
    for i, yr in enumerate(all_years):
        if value_is_actual[i]:
            col_source_map["Value (EUR)"][i] = "input"
        elif f"reits_valuations::{i}::Value (EUR)" in stored_formulas:
            col_source_map["Value (EUR)"][i] = "input"
        cap = get_new_capital(yr)
        if cap != 0 and yr < utils.CURRENT_YEAR:
            col_source_map["New Capital"][i] = "input"
        elif f"reits_valuations::{i}::New Capital" in stored_formulas:
            col_source_map["New Capital"][i] = "input"

    bg_style_map, cell_style_map = utils.build_valuation_style_maps(col_source_map)
    formula_map = utils.get_formula_map("reits_valuations", len(proj_df), ["Value (EUR)", "New Capital"])

    st.caption("🟡 Yellow = user input. Default = formula. Double-click to edit. Supports math (e.g. =500*2).")
    grid_result = utils.render_editable_aggrid_table(
        proj_df, key="reit_valuation_aggrid",
        editable_cols=["Value (EUR)", "New Capital"],
        numeric_cols=["Value (EUR)", "New Capital"],
        bg_style_map=bg_style_map, cell_style_map=cell_style_map,
        formula_map=formula_map, editor_key="reits_valuations",
        height=min(500, max(200, len(rows) * 28 + 40)),
    )
    edited = grid_result.data
    edited = utils.process_math_in_df(edited, ["Value (EUR)", "New Capital"], editor_key="reits_valuations")

    if st.button("💾 Save Changes", type="primary", key="reit_val_save"):
        avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
        reit_hist_save = avh.get("REITs", {})
        for i, (_, row) in enumerate(edited.iterrows()):
            yr = int(row["Year"])
            yr_str = str(yr)
            new_val = float(row.get("Value (EUR)", 0) or 0)
            orig_val = float(orig_df.iloc[i]["Value (EUR)"])
            if abs(new_val - orig_val) > 0.5:
                if new_val > 0:
                    reit_hist_save[yr_str] = new_val
                else:
                    reit_hist_save.pop(yr_str, None)
        avh["REITs"] = reit_hist_save
        utils.save_json(utils.DATA_DIR / "asset_value_history.json", avh)

        plan = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
        by_year = plan.get("planned_investment_by_year", {})
        ac_years = by_year.get("REITs", {})
        for i, (_, row) in enumerate(edited.iterrows()):
            yr = int(row["Year"])
            yr_str = str(yr)
            new_cap = float(row.get("New Capital", 0) or 0)
            orig_cap = float(orig_df.iloc[i]["New Capital"])
            if abs(new_cap - orig_cap) > 0.5:
                ac_years[yr_str] = new_cap
        by_year["REITs"] = ac_years
        plan["planned_investment_by_year"] = by_year
        utils.save_json(utils.DATA_DIR / "investment_plan.json", plan)
        st.success("Saved!")
        st.rerun()

    # Chart
    import plotly.graph_objects as go
    fig = go.Figure()
    actual_x = [all_years[i] for i in range(len(all_years)) if value_is_actual[i]]
    actual_y = [values[i] for i in range(len(values)) if value_is_actual[i]]
    proj_x = [all_years[i] for i in range(len(all_years)) if not value_is_actual[i] and values[i] > 0]
    proj_y = [values[i] for i in range(len(values)) if not value_is_actual[i] and values[i] > 0]
    if actual_x:
        fig.add_trace(go.Scatter(x=actual_x, y=actual_y, mode="lines+markers", name="Actual",
                                  line=dict(color="#f59e0b", width=3),
                                  text=[utils.fmt_eur(v) for v in actual_y], hovertemplate="%{x}: %{text}"))
    if proj_x:
        fig.add_trace(go.Scatter(x=proj_x, y=proj_y, mode="lines+markers", name="Projected",
                                  line=dict(color="#4c8bf5", width=2, dash="dot"),
                                  text=[utils.fmt_eur(v) for v in proj_y], hovertemplate="%{x}: %{text}"))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0e1117",
                      plot_bgcolor="#1a1f2e", xaxis_title="Year",
                      yaxis_title="Value (EUR)", yaxis=dict(tickformat=",.0f"),
                      title=f"REITs Valuation ({scenario})")
    st.plotly_chart(fig, use_container_width=True)

