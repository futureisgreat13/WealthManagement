import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("📈 Equity")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)
utils.render_year_end_alert("Equity")
utils.show_unsaved_warning()

positions = utils.load_json(utils.DATA_DIR / "public_stocks.json", [])
stocks = [p for p in positions if p.get("type") in ("Equity", "ETF")]

# --- Unclassified symbol detection ---
classifications = utils.load_symbol_classifications()
unclassified_syms = []
for p in stocks:
    sym = p.get("ticker", "")
    if sym and utils.classify_symbol(sym, classifications) == "Public Stock" and sym not in classifications:
        unclassified_syms.append(sym)

if unclassified_syms:
    with st.expander(f"🔴 **{len(unclassified_syms)} unclassified symbol(s)** — click to classify", expanded=True):
        categories = ["Public Stock", "ETF", "REIT", "Bond", "Precious Metal"]
        user_cls = {}
        for sym in sorted(set(unclassified_syms)):
            cols = st.columns([2, 2, 3])
            cols[0].code(sym)
            sg = utils.verify_symbol_classification(sym)
            confidence_icon = "🟢" if sg["confidence"] == "high" else "🟡" if sg["confidence"] == "medium" else "🔴"
            cols[1].markdown(f"{confidence_icon} Suggested: **{sg['suggested']}**")
            default_idx = categories.index(sg["suggested"]) if sg["suggested"] in categories else 0
            user_cls[sym] = cols[2].selectbox(
                f"Cat {sym}", categories, index=default_idx,
                key=f"eq_classify_{sym}", label_visibility="collapsed")
        if st.button("✅ Save Classifications", type="primary", key="eq_save_classify"):
            for sym, cat in user_cls.items():
                if cat != "Public Stock":
                    utils.save_symbol_classification(sym, cat)
            st.success(f"✅ Saved! Positions will be reclassified on next IBKR import.")
            st.rerun()

# --- Metrics: show latest IBKR year-end data if available ---
avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
equity_hist = avh.get("Equity", {})
etf_hist = avh.get("ETF", {})
all_ibkr_years = sorted(set(equity_hist.keys()) | set(etf_hist.keys()))
ibkr_db = utils.load_ibkr_database()

if all_ibkr_years:
    latest_yr = all_ibkr_years[-1]
    total_val = equity_hist.get(latest_yr, 0) + etf_hist.get(latest_yr, 0)
    yr_data = ibkr_db.get(latest_yr, {})
    if yr_data:
        pos_by_class = yr_data.get("positions_by_class", {})
        all_pos = []
        for ac_positions in pos_by_class.values():
            all_pos.extend(ac_positions)
        stock_pos = [p for p in all_pos if p.get("category") in ("Public Stock", "ETF")]
        total_cost = sum(p.get("cost_eur", 0) for p in stock_pos)
        total_div = sum(yr_data.get("dividends_by_class", {}).get(ac, 0)
                       for ac in ["Equity"])
    else:
        total_cost = sum(p.get("cost_eur", 0) for p in stocks)
        total_div = sum(p.get("net_div_eur", 0) for p in stocks)
    year_label = f" ({latest_yr} YE)"
else:
    total_val = sum(p.get("value_eur", 0) for p in stocks)
    total_cost = sum(p.get("cost_eur", 0) for p in stocks)
    total_div = sum(p.get("net_div_eur", 0) for p in stocks)
    year_label = ""

total_pnl = total_val - total_cost

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Total Value{year_label}", utils.fmt_eur(total_val))
c2.metric("Total Cost", utils.fmt_eur(total_cost))
c3.metric("Total P&L", utils.fmt_eur(total_pnl))
c4.metric("Annual Dividends", utils.fmt_eur(total_div))

st.divider()

tab1, tab2 = st.tabs(["Positions", "Valuations"])

with tab1:
    if not stocks:
        st.info("No positions yet.")
    else:
        rows = []
        for p in stocks:
            rows.append({
                "Ticker": p.get("ticker", ""),
                "Name": p.get("name", ""),
                "Type": p.get("type", ""),
                "Ccy": p.get("currency", ""),
                "Qty": p.get("quantity", 0),
                "Cost (EUR)": utils.fmt_eur_short(p.get("cost_eur", 0)),
                "Value (EUR)": utils.fmt_eur_short(p.get("value_eur", 0)),
                "P&L (EUR)": utils.fmt_eur_short(p.get("value_eur", 0) - p.get("cost_eur", 0)),
                "Return %": f"{p.get('return_pct', 0):+.1f}%",
                "Div/yr (EUR)": utils.fmt_eur_short(p.get("net_div_eur", 0)),
            })
        df = pd.DataFrame(rows)
        utils.render_aggrid_table(df, key="aggrid_stocks_positions", height=min(400, max(200, len(rows) * 32 + 40)))

with tab2:
    st.subheader("Valuations — Historical & Projected")

    avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
    _eq_hist = avh.get("Equity", {})
    _etf_hist = avh.get("ETF", {})
    equity_history = {}
    for yr_str in set(list(_eq_hist.keys()) + list(_etf_hist.keys())):
        equity_history[yr_str] = _eq_hist.get(yr_str, 0) + _etf_hist.get(yr_str, 0)

    scenario = st.selectbox("Scenario", utils.SCENARIOS, index=2, key="eq_proj_scenario")
    assumptions = utils.load_assumptions()
    return_pct = utils.get_return_pct("Equity", scenario, assumptions)
    st.info(f"Expected return: {return_pct:.1f}% — set in ⚙️ FX & Settings > Liquid Asset Scenario Returns")

    # Build timeline using shared helper
    plan = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
    planned_equity = plan.get("planned_investment_yr", {}).get("Equity", 0)

    def get_new_capital(yr):
        return utils.get_valuation_new_capital("Equity", "Equity", yr)

    def get_capital_source(yr):
        """Return human-readable source description for New Capital."""
        plan_data = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
        by_yr = plan_data.get("planned_investment_by_year", {}).get("Equity", {}).get(str(yr))
        if by_yr is not None:
            ibkr_val = utils.get_ibkr_new_capital("Equity", yr)
            if ibkr_val is not None and abs(ibkr_val - by_yr) < 0.5:
                return "IBKR import"
            return "Manual override (Valuations tab)"
        ibkr_val = utils.get_ibkr_new_capital("Equity", yr)
        if ibkr_val is not None:
            return "IBKR import"
        if yr >= utils.CURRENT_YEAR:
            return f"Investment Plan default (€{planned_equity:,.0f}/yr)"
        return "—"

    hist_years = sorted([int(y) for y in equity_history.keys() if equity_history[y] > 0])
    start_year = min(hist_years) if hist_years else 2020
    end_year = max(utils.CURRENT_YEAR + 9, max(hist_years) + 5 if hist_years else 2034)
    all_years = list(range(start_year, end_year + 1))

    values = utils.compute_liquid_timeline("Equity", all_years, scenario)
    value_is_actual = []
    for yr in all_years:
        actual = equity_history.get(str(yr))
        value_is_actual.append(actual is not None and actual > 0)

    # Build editable DataFrame
    rows = []
    for i, yr in enumerate(all_years):
        rows.append({
            "Year": yr,
            "Value (EUR)": round(values[i]),
            "New Capital": round(get_new_capital(yr)),
        })

    proj_df = pd.DataFrame(rows)
    orig_df = proj_df.copy()

    # Build per-cell coloring: yellow=user input, blue=IBKR, default=formula
    col_source_map = {"Value (EUR)": {}, "New Capital": {}}
    stored_formulas = utils.load_json(utils.DATA_DIR / "formulas.json", {})
    for i, yr in enumerate(all_years):
        # Value column
        if value_is_actual[i]:
            ibkr_val = utils.get_ibkr_new_capital("Equity", yr)
            col_source_map["Value (EUR)"][i] = "ibkr" if ibkr_val is not None else "input"
        elif f"public_stocks_valuations::{i}::Value (EUR)" in stored_formulas:
            col_source_map["Value (EUR)"][i] = "input"
        # New Capital column
        cap_src = get_capital_source(yr)
        if "IBKR" in cap_src:
            col_source_map["New Capital"][i] = "ibkr"
        elif "Manual" in cap_src or (yr < utils.CURRENT_YEAR and get_new_capital(yr) != 0):
            col_source_map["New Capital"][i] = "input"
        elif f"public_stocks_valuations::{i}::New Capital" in stored_formulas:
            col_source_map["New Capital"][i] = "input"

    bg_style_map, cell_style_map = utils.build_valuation_style_maps(col_source_map)
    formula_map = utils.get_formula_map("public_stocks_valuations", len(proj_df), ["Value (EUR)", "New Capital"])

    st.caption("🟡 Yellow = user input. 🔵 Blue = IBKR import. Default = formula. Double-click to edit. Supports math (e.g. =500*2, 1000/EURUSD).")
    _orig_stock_val = proj_df.copy()
    grid_result = utils.render_editable_aggrid_table(
        proj_df, key="eq_valuation_aggrid",
        editable_cols=["Value (EUR)", "New Capital"],
        numeric_cols=["Value (EUR)", "New Capital"],
        bg_style_map=bg_style_map,
        cell_style_map=cell_style_map,
        formula_map=formula_map,
        editor_key="public_stocks_valuations",
        height=min(500, max(200, len(rows) * 28 + 40)),
    )
    edited = grid_result.data
    edited = utils.process_math_in_df(edited, ["Value (EUR)", "New Capital"], editor_key="public_stocks_valuations")
    utils.track_unsaved_changes("stock_val", _orig_stock_val, edited)

    if st.button("💾 Save Changes", type="primary", key="eq_val_save"):
        # Save year-end value overrides
        avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
        for i, (_, row) in enumerate(edited.iterrows()):
            yr = int(row["Year"])
            yr_str = str(yr)
            new_val = float(row.get("Value (EUR)", 0) or 0)
            orig_val = float(orig_df.iloc[i]["Value (EUR)"])
            if abs(new_val - orig_val) > 0.5:  # Value was edited
                if new_val > 0:
                    # Preserve existing Equity/ETF split ratio
                    old_eq = avh.get("Equity", {}).get(yr_str, 0)
                    old_etf = avh.get("ETF", {}).get(yr_str, 0)
                    old_total = old_eq + old_etf
                    if old_total > 0:
                        eq_ratio = old_eq / old_total
                        avh.setdefault("Equity", {})[yr_str] = round(new_val * eq_ratio)
                        avh.setdefault("ETF", {})[yr_str] = round(new_val * (1 - eq_ratio))
                    else:
                        avh.setdefault("Equity", {})[yr_str] = round(new_val)
                else:
                    avh.get("Equity", {}).pop(yr_str, None)
                    avh.get("ETF", {}).pop(yr_str, None)
        utils.save_json(utils.DATA_DIR / "asset_value_history.json", avh)

        # Save new capital overrides
        plan = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
        by_year = plan.get("planned_investment_by_year", {})
        ac_years = by_year.get("Equity", {})
        for i, (_, row) in enumerate(edited.iterrows()):
            yr = int(row["Year"])
            yr_str = str(yr)
            new_cap = float(row.get("New Capital", 0) or 0)
            orig_cap = float(orig_df.iloc[i]["New Capital"])
            if abs(new_cap - orig_cap) > 0.5:  # Capital was edited
                ac_years[yr_str] = new_cap
        by_year["Equity"] = ac_years
        plan["planned_investment_by_year"] = by_year
        utils.save_json(utils.DATA_DIR / "investment_plan.json", plan)
        utils.clear_unsaved("stock_val")
        st.success("Saved!")
        st.rerun()

    # Data source info
    with st.expander("ℹ️ Data Sources"):
        st.markdown("**Per-row source info:**")
        for i, yr in enumerate(all_years):
            if value_is_actual[i] or get_new_capital(yr) != 0:
                val_src = "🟡 Actual (IBKR/manual)" if value_is_actual[i] else "⚪ Formula"
                cap_src = get_capital_source(yr)
                st.markdown(f"- **{yr}**: Value = {val_src} | New Capital = {cap_src}")

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
                      title=f"Equity+ETF Valuation ({scenario})")
    st.plotly_chart(fig, use_container_width=True)

