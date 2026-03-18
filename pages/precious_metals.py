import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("🥇 Precious Metals")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)
utils.render_year_end_alert("Precious Metals")

positions = utils.load_json(utils.DATA_DIR / "public_stocks.json", [])
metals = [p for p in positions if p.get("type") == "Precious Metals"]

# --- Metrics ---
avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
pm_hist = avh.get("Precious Metals", {})
all_ibkr_years = sorted(pm_hist.keys())

if all_ibkr_years:
    latest_yr = all_ibkr_years[-1]
    total_val = pm_hist.get(latest_yr, 0)
    year_label = f" ({latest_yr} YE)"
else:
    total_val = sum(p.get("value_eur", 0) for p in metals)
    year_label = ""

total_cost = sum(p.get("cost_eur", 0) for p in metals)
total_pnl = total_val - total_cost
total_div = sum(p.get("net_div_eur", 0) for p in metals)

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Total Value{year_label}", utils.fmt_eur(total_val))
c2.metric("Total Cost", utils.fmt_eur(total_cost))
c3.metric("P&L", utils.fmt_eur(total_pnl))
c4.metric("Dividends/yr", utils.fmt_eur(total_div))

st.divider()

tab1, tab2 = st.tabs(["Positions", "Valuations"])

with tab1:
    if not metals:
        st.info("No precious metals positions yet.")
    else:
        rows = []
        for p in metals:
            rows.append({
                "Ticker": p.get("ticker", ""),
                "Name": p.get("name", ""),
                "Ccy": p.get("currency", ""),
                "Qty": p.get("quantity", 0),
                "Cost (EUR)": utils.fmt_eur_short(p.get("cost_eur", 0)),
                "Value (EUR)": utils.fmt_eur_short(p.get("value_eur", 0)),
                "P&L (EUR)": utils.fmt_eur_short(p.get("value_eur", 0) - p.get("cost_eur", 0)),
                "Return %": f"{p.get('return_pct', 0):+.1f}%",
                "Div/yr": utils.fmt_eur_short(p.get("net_div_eur", 0)),
            })
        df = pd.DataFrame(rows)
        utils.render_aggrid_table(df, key="aggrid_metals_positions", height=min(400, max(200, len(rows) * 32 + 40)))

with tab2:
    st.subheader("Valuations — Historical & Projected")
    st.caption("🟡 Actual = imported from IBKR or manually entered. "
               "⚪ Formula = V(N-1) × (1 + return%) + new capital. All cells are editable.")

    avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
    metals_history = avh.get("Precious Metals", {})

    scenario = st.selectbox("Scenario", utils.SCENARIOS, index=2, key="metals_proj_scenario")
    assumptions = utils.load_assumptions()
    return_pct = utils.get_return_pct("Precious Metals", scenario, assumptions)
    st.info(f"Expected return: {return_pct:.1f}% — set in ⚙️ FX & Settings > Liquid Asset Scenario Returns")

    plan = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
    planned_metals = plan.get("planned_investment_yr", {}).get("Precious Metals", 0)

    def get_new_capital(yr):
        return utils.get_valuation_new_capital("Precious Metals", "Precious Metals", yr)

    hist_years = sorted([int(y) for y in metals_history.keys() if metals_history[y] > 0])
    start_year = min(hist_years) if hist_years else 2020
    end_year = max(utils.CURRENT_YEAR + 9, max(hist_years) + 5 if hist_years else 2034)
    all_years = list(range(start_year, end_year + 1))

    values = utils.compute_liquid_timeline("Precious Metals", all_years, scenario)
    value_is_actual = []
    for yr in all_years:
        actual = metals_history.get(str(yr))
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
        elif f"precious_metals_valuations::{i}::Value (EUR)" in stored_formulas:
            col_source_map["Value (EUR)"][i] = "input"
        cap = get_new_capital(yr)
        if cap != 0 and yr < utils.CURRENT_YEAR:
            col_source_map["New Capital"][i] = "input"
        elif f"precious_metals_valuations::{i}::New Capital" in stored_formulas:
            col_source_map["New Capital"][i] = "input"

    bg_style_map, cell_style_map = utils.build_valuation_style_maps(col_source_map)
    formula_map = utils.get_formula_map("precious_metals_valuations", len(proj_df), ["Value (EUR)", "New Capital"])

    st.caption("🟡 Yellow = user input. Default = formula. Double-click to edit. Supports math (e.g. =500*2).")
    grid_result = utils.render_editable_aggrid_table(
        proj_df, key="metals_valuation_aggrid",
        editable_cols=["Value (EUR)", "New Capital"],
        numeric_cols=["Value (EUR)", "New Capital"],
        bg_style_map=bg_style_map, cell_style_map=cell_style_map,
        formula_map=formula_map, editor_key="precious_metals_valuations",
        height=min(500, max(200, len(rows) * 28 + 40)),
    )
    edited = grid_result.data
    edited = utils.process_math_in_df(edited, ["Value (EUR)", "New Capital"], editor_key="precious_metals_valuations")

    if st.button("💾 Save Changes", type="primary", key="metals_val_save"):
        avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
        pm_hist_save = avh.get("Precious Metals", {})
        for i, (_, row) in enumerate(edited.iterrows()):
            yr = int(row["Year"])
            yr_str = str(yr)
            new_val = float(row.get("Value (EUR)", 0) or 0)
            orig_val = float(orig_df.iloc[i]["Value (EUR)"])
            if abs(new_val - orig_val) > 0.5:
                if new_val > 0:
                    pm_hist_save[yr_str] = new_val
                else:
                    pm_hist_save.pop(yr_str, None)
        avh["Precious Metals"] = pm_hist_save
        utils.save_json(utils.DATA_DIR / "asset_value_history.json", avh)

        plan = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
        by_year = plan.get("planned_investment_by_year", {})
        ac_years = by_year.get("Precious Metals", {})
        for i, (_, row) in enumerate(edited.iterrows()):
            yr = int(row["Year"])
            yr_str = str(yr)
            new_cap = float(row.get("New Capital", 0) or 0)
            orig_cap = float(orig_df.iloc[i]["New Capital"])
            if abs(new_cap - orig_cap) > 0.5:
                ac_years[yr_str] = new_cap
        by_year["Precious Metals"] = ac_years
        plan["planned_investment_by_year"] = by_year
        utils.save_json(utils.DATA_DIR / "investment_plan.json", plan)
        st.success("Saved!")
        st.rerun()

    with st.expander("ℹ️ Data Sources"):
        st.markdown(f"**Return %**: {return_pct:.1f}% ({scenario}) — set in ⚙️ FX & Settings")
        st.markdown(f"**Default New Capital**: €{planned_metals:,.0f}/yr — set in 📊 Investment Plan")

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
                                  line=dict(color="#FFD700", width=2, dash="dot"),
                                  text=[utils.fmt_eur(v) for v in proj_y], hovertemplate="%{x}: %{text}"))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0e1117",
                      plot_bgcolor="#1a1f2e", xaxis_title="Year",
                      yaxis_title="Value (EUR)", yaxis=dict(tickformat=",.0f"),
                      title=f"Precious Metals Valuation ({scenario})")
    st.plotly_chart(fig, use_container_width=True)

