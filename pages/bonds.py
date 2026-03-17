import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("📄 Bonds")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)

items = utils.load_json(utils.DATA_DIR / "bonds.json", [])

def compute_ytm(face, price, coupon_rate, maturity_str):
    try:
        mat = datetime.strptime(maturity_str, "%Y-%m-%d")
        years = max((mat - datetime.now()).days / 365, 0.01)
        coupon = face * coupon_rate / 100
        ytm = (coupon + (face - price) / years) / ((face + price) / 2) * 100
        return round(ytm, 2)
    except Exception:
        return 0.0

# --- Metrics ---
avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
bonds_hist = avh.get("Bonds", {})
ah = utils.load_json(utils.DATA_DIR / "asset_history.json", {})
ah_bonds = ah.get("Bonds", {})
for yr, val in ah_bonds.items():
    if yr not in bonds_hist and val > 0:
        bonds_hist[yr] = val
all_ye_years = sorted(bonds_hist.keys())

if all_ye_years:
    latest_yr = all_ye_years[-1]
    total_val = bonds_hist.get(latest_yr, 0)
    year_label = f" ({latest_yr} YE)"
else:
    total_val = sum(i.get("current_value_eur", 0) for i in items)
    year_label = ""

annual_income = sum(i.get("face_value", 0) * i.get("coupon_rate_pct", 0) / 100 for i in items)
total_cost = sum(i.get("purchase_price", 0) for i in items)

c1, c2, c3 = st.columns(3)
c1.metric(f"Total Value{year_label}", utils.fmt_eur(total_val))
c2.metric("Annual Coupon Income", utils.fmt_eur(annual_income))
c3.metric("Total Cost", utils.fmt_eur(total_cost))

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["Positions", "Valuations", "Edit"])

with tab1:
    if not items:
        st.info("No bonds yet. Add them in the Edit tab or import via IB CSV.")
    else:
        rows = []
        for b in items:
            ytm = compute_ytm(b.get("face_value", 0), b.get("purchase_price", 0),
                              b.get("coupon_rate_pct", 0), b.get("maturity_date", "2030-01-01"))
            rows.append({
                "Name": b.get("name", ""),
                "Currency": b.get("currency", "EUR"),
                "Face Value": utils.fmt_eur_short(b.get("face_value", 0)),
                "Purchase Price": utils.fmt_eur_short(b.get("purchase_price", 0)),
                "Coupon %": b.get("coupon_rate_pct", 0),
                "Maturity": b.get("maturity_date", ""),
                "Current Value (EUR)": utils.fmt_eur_short(b.get("current_value_eur", 0)),
                "YTM %": ytm,
            })
        df = pd.DataFrame(rows)
        utils.render_aggrid_table(df, key="aggrid_bonds_positions", height=300)

with tab2:
    st.subheader("Valuations — Historical & Projected")
    st.caption("🟡 Actual = imported or manually entered. "
               "⚪ Formula = V(N-1) × (1 + return%) + new capital. All cells are editable.")

    avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
    bonds_history = avh.get("Bonds", {})
    ah = utils.load_json(utils.DATA_DIR / "asset_history.json", {})
    ah_bonds = ah.get("Bonds", {})
    for yr, val in ah_bonds.items():
        if yr not in bonds_history and val > 0:
            bonds_history[yr] = val

    scenario = st.selectbox("Scenario", utils.SCENARIOS, index=2, key="bonds_proj_scenario")
    assumptions = utils.load_assumptions()
    return_pct = utils.get_return_pct("Bonds", scenario, assumptions)
    st.info(f"Expected return: {return_pct:.1f}% — set in ⚙️ FX & Settings > Liquid Asset Scenario Returns")

    plan = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
    planned_bonds = plan.get("planned_investment_yr", {}).get("Bonds", 0)

    def get_new_capital(yr):
        return utils.get_valuation_new_capital("Bonds", "Bond", yr)

    hist_years = sorted([int(y) for y in bonds_history.keys() if bonds_history[y] > 0])
    start_year = min(hist_years) if hist_years else 2020
    end_year = max(utils.CURRENT_YEAR + 9, max(hist_years) + 5 if hist_years else 2034)
    all_years = list(range(start_year, end_year + 1))

    values = utils.compute_liquid_timeline("Bonds", all_years, scenario)
    value_is_actual = []
    for yr in all_years:
        actual = bonds_history.get(str(yr))
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

    # Styled read-only display with yellow highlighting for actual values
    display_df = proj_df.copy()
    display_df["Year"] = display_df["Year"].astype(int)

    def highlight_actuals(row):
        idx = display_df.index.get_loc(row.name)
        if idx < len(value_is_actual) and value_is_actual[idx]:
            return ["background-color: rgba(255, 200, 0, 0.25); color: #ffd700"] * len(row)
        return [""] * len(row)

    styled = display_df.style.apply(highlight_actuals, axis=1).format({
        "Year": "{:.0f}", "Value (EUR)": "€{:,.0f}", "New Capital": "{:,.0f}",
    })
    st.caption("🟡 Yellow = actual values (IBKR/manual). White = formula: V(N-1) × (1+return%) + New Capital.")
    st.dataframe(styled, use_container_width=True, hide_index=True,
        column_config={
            "Value (EUR)": st.column_config.TextColumn(
                help="🟡 Yellow = actual (from IBKR or manual entry)\n⚪ White = formula"),
            "New Capital": st.column_config.TextColumn(
                help="Source priority: Manual override > IBKR import > Investment Plan default (€{:,.0f}/yr)".format(planned_bonds)),
        })

    st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Edit values below — supports math (e.g. 500*2, 1000/EURUSD). Negative New Capital = money withdrawn.</p>', unsafe_allow_html=True)
    proj_df = utils.inject_formulas_for_edit(proj_df, "bonds_valuations", ["Value (EUR)", "New Capital"])
    edited_vh = st.data_editor(proj_df, use_container_width=True, hide_index=True,
        column_config={
            "Year": st.column_config.TextColumn("Year"),
            "Value (EUR)": st.column_config.TextColumn("Value (EUR)"),
            "New Capital": st.column_config.TextColumn("New Capital"),
        },
        disabled=["Year"], key="bonds_valuation_editor")
    edited_vh = utils.process_math_in_df(edited_vh, ["Value (EUR)", "New Capital"], editor_key="bonds_valuations")

    if st.button("💾 Save Changes", type="primary", key="bonds_val_save"):
        avh = utils.load_json(utils.DATA_DIR / "asset_value_history.json", {})
        bonds_hist_save = avh.get("Bonds", {})
        for i, (_, row) in enumerate(edited_vh.iterrows()):
            yr = int(row["Year"])
            yr_str = str(yr)
            new_val = float(row.get("Value (EUR)", 0) or 0)
            orig_val = float(orig_df.iloc[i]["Value (EUR)"])
            if abs(new_val - orig_val) > 0.5:
                if new_val > 0:
                    bonds_hist_save[yr_str] = new_val
                else:
                    bonds_hist_save.pop(yr_str, None)
        avh["Bonds"] = bonds_hist_save
        utils.save_json(utils.DATA_DIR / "asset_value_history.json", avh)

        plan = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
        by_year = plan.get("planned_investment_by_year", {})
        ac_years = by_year.get("Bonds", {})
        for i, (_, row) in enumerate(edited_vh.iterrows()):
            yr = int(row["Year"])
            yr_str = str(yr)
            new_cap = float(row.get("New Capital", 0) or 0)
            orig_cap = float(orig_df.iloc[i]["New Capital"])
            if abs(new_cap - orig_cap) > 0.5:
                ac_years[yr_str] = new_cap
        by_year["Bonds"] = ac_years
        plan["planned_investment_by_year"] = by_year
        utils.save_json(utils.DATA_DIR / "investment_plan.json", plan)
        st.success("Saved!")
        st.rerun()

    with st.expander("ℹ️ Data Sources"):
        st.markdown(f"**Return %**: {return_pct:.1f}% ({scenario}) — set in ⚙️ FX & Settings")
        st.markdown(f"**Default New Capital**: €{planned_bonds:,.0f}/yr — set in 📊 Investment Plan")

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
                                  line=dict(color="#60a5fa", width=2, dash="dot"),
                                  text=[utils.fmt_eur(v) for v in proj_y], hovertemplate="%{x}: %{text}"))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0e1117",
                      plot_bgcolor="#1a1f2e", xaxis_title="Year",
                      yaxis_title="Value (EUR)", yaxis=dict(tickformat=",.0f"),
                      title=f"Bonds Valuation ({scenario})")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Edit Bonds")
    edit_rows = [{
        "name": b.get("name", ""), "currency": b.get("currency", "EUR"),
        "face_value": b.get("face_value", 0), "purchase_price": b.get("purchase_price", 0),
        "coupon_rate_pct": b.get("coupon_rate_pct", 0),
        "maturity_date": b.get("maturity_date", ""), "current_value_eur": b.get("current_value_eur", 0),
    } for b in items]

    edit_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(
        columns=["name", "currency", "face_value", "purchase_price", "coupon_rate_pct", "maturity_date", "current_value_eur"])
    st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter your values below</p>', unsafe_allow_html=True)
    edit_df = utils.inject_formulas_for_edit(edit_df, "bonds_holdings", ["face_value", "purchase_price", "coupon_rate_pct", "current_value_eur"])
    edited = st.data_editor(edit_df, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "currency": st.column_config.SelectboxColumn("Currency", options=utils.CURRENCIES),
            "face_value": st.column_config.TextColumn("face_value"),
            "purchase_price": st.column_config.TextColumn("purchase_price"),
            "current_value_eur": st.column_config.TextColumn("current_value_eur"),
        })
    edited = utils.process_math_in_df(edited, ["face_value", "purchase_price", "coupon_rate_pct", "current_value_eur"], editor_key="bonds_holdings")

    if st.button("💾 Save Bonds", type="primary", key="bonds_save"):
        new_items = []
        for j, (_, row) in enumerate(edited.iterrows()):
            if row.get("name"):
                orig = items[j] if j < len(items) else {}
                new_items.append({
                    "id": orig.get("id", utils.new_id()),
                    "name": row["name"], "currency": row.get("currency", "EUR"),
                    "face_value": float(row.get("face_value", 0) or 0),
                    "purchase_price": float(row.get("purchase_price", 0) or 0),
                    "coupon_rate_pct": float(row.get("coupon_rate_pct", 0) or 0),
                    "maturity_date": str(row.get("maturity_date", "") or ""),
                    "current_value_eur": float(row.get("current_value_eur", 0) or 0),
                })
        utils.save_json(utils.DATA_DIR / "bonds.json", new_items)
        st.success("Saved!")
        st.rerun()
