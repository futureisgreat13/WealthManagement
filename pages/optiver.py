import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("⚡ Optiver")

data = utils.load_json(utils.DATA_DIR / "optiver.json", {
    "free_share_price": 10000, "bound_share_price": 3631,
    "free_shares": [], "bound_shares": [], "dividends": [],
    "scenario_appreciation": {"super_bear": 0, "bear": 5, "base": 10, "bull": 18},
    "year_end_values": {},
})

free_price = data.get("free_share_price", 10000)
bound_price = data.get("bound_share_price", 3631)
free_count = sum(s.get("shares_added", 0) for s in data.get("free_shares", []))
bound_count = sum(s.get("shares_added", 0) for s in data.get("bound_shares", []))
total_val = free_count * free_price + bound_count * bound_price
year_end_values = data.get("year_end_values", {})

c1, c2, c3 = st.columns(3)
c1.metric("Total Optiver Value", utils.fmt_eur(total_val))
c2.metric("Free Shares", f"{free_count} × {utils.fmt_eur(free_price)}")
c3.metric("Bound Shares", f"{bound_count} × {utils.fmt_eur(bound_price)}")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Free Shares", "Bound Shares", "Dividends", "Valuations"])

def shares_editor(tab_key: str, share_list: list, price_key: str, price_val: float):
    new_price = st.number_input("Share Price (EUR)", value=float(price_val), step=100.0, key=f"price_{tab_key}")

    df = pd.DataFrame(share_list if share_list else [], columns=["id", "year", "shares_added", "invested_amount"])
    if df.empty:
        df = pd.DataFrame(columns=["id", "year", "shares_added", "invested_amount"])

    display_df = df[["year", "shares_added", "invested_amount"]].copy() if not df.empty else pd.DataFrame(columns=["year", "shares_added", "invested_amount"])

    st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
    editor_key = f"optiver_{tab_key}_shares"
    edited = st.data_editor(display_df, width="stretch", hide_index=True, num_rows="dynamic",
        column_config={
            "year": st.column_config.NumberColumn("Year", format="%d"),
            "shares_added": st.column_config.NumberColumn("Shares Added"),
            "invested_amount": st.column_config.NumberColumn("Invested (EUR)", format="€%.0f"),
        })
    edited = utils.process_math_in_df(edited, ["shares_added", "invested_amount"], editor_key=editor_key)
    return new_price, edited

with tab1:
    new_free_price, edited_free = shares_editor("free", data.get("free_shares", []), "free_share_price", free_price)

with tab2:
    new_bound_price, edited_bound = shares_editor("bound", data.get("bound_shares", []), "bound_share_price", bound_price)

with tab3:
    divs = data.get("dividends", [])
    div_df = pd.DataFrame(divs if divs else [], columns=["id", "year", "div_per_share", "shares_eligible", "tax", "net_dividend"])
    display_div = div_df[["year", "div_per_share", "shares_eligible", "tax", "net_dividend"]].copy() if not div_df.empty else pd.DataFrame(columns=["year", "div_per_share", "shares_eligible", "tax", "net_dividend"])
    st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
    edited_divs = st.data_editor(display_div, width="stretch", hide_index=True, num_rows="dynamic",
        column_config={
            "year": st.column_config.NumberColumn("Year", format="%d"),
            "div_per_share": st.column_config.NumberColumn("Div/Share (EUR)", format="€%.0f"),
            "shares_eligible": st.column_config.NumberColumn("Eligible Shares"),
            "tax": st.column_config.NumberColumn("Tax (EUR)", format="€%.0f"),
            "net_dividend": st.column_config.NumberColumn("Net Dividend (EUR)", format="€%.0f"),
        })
    edited_divs = utils.process_math_in_df(edited_divs, ["div_per_share", "shares_eligible", "tax", "net_dividend"], editor_key="optiver_dividends")

with tab4:
    st.subheader("Valuations")
    st.caption("🟡 Yellow = manually entered year-end value. White = projected via formula. "
               "Projection: V(N) = V(N-1) × (1 + appreciation%). "
               "Enter year-end actuals below to override projections.")

    scenario = st.selectbox("Scenario", utils.SCENARIOS, index=2, key="optiver_scenario")
    scen_ap = data.get("scenario_appreciation", {})
    scen_key = utils.SCENARIO_KEYS.get(scenario, "base")
    appreciation = scen_ap.get(scen_key, 10)

    st.info(f"Appreciation rate: {appreciation:.1f}% ({scenario})")

    # Compute cumulative shares per year for free and bound
    free_shares_list = data.get("free_shares", [])
    bound_shares_list = data.get("bound_shares", [])

    all_share_years = set()
    for s in free_shares_list:
        all_share_years.add(s.get("year", 2020))
    for s in bound_shares_list:
        all_share_years.add(s.get("year", 2020))
    for yr_str in year_end_values.keys():
        all_share_years.add(int(yr_str))

    if all_share_years:
        start_year = min(all_share_years)
    else:
        start_year = 2020
    end_year = utils.CURRENT_YEAR + 10
    all_years = list(range(start_year, end_year + 1))

    # Compute cumulative shares per year
    def cum_shares_at_year(share_list, yr):
        return sum(s.get("shares_added", 0) for s in share_list if s.get("year", 9999) <= yr)

    # Build free and bound value rows
    free_yev = year_end_values.get("free", {})
    bound_yev = year_end_values.get("bound", {})

    free_values = []
    bound_values = []
    free_is_actual = []
    bound_is_actual = []

    prev_free = 0
    prev_bound = 0

    for yr in all_years:
        yr_str = str(yr)
        # Free shares
        free_actual = free_yev.get(yr_str)
        has_free_actual = free_actual is not None and free_actual > 0
        if has_free_actual:
            fv = free_actual
            free_is_actual.append(True)
        elif prev_free > 0:
            fv = prev_free * (1 + appreciation / 100)
            free_is_actual.append(False)
        else:
            # Use share count × price as starting point
            fc = cum_shares_at_year(free_shares_list, yr)
            fv = fc * free_price if fc > 0 else 0
            free_is_actual.append(False)
        free_values.append(round(fv))
        prev_free = fv

        # Bound shares
        bound_actual = bound_yev.get(yr_str)
        has_bound_actual = bound_actual is not None and bound_actual > 0
        if has_bound_actual:
            bv = bound_actual
            bound_is_actual.append(True)
        elif prev_bound > 0:
            bv = prev_bound * (1 + appreciation / 100)
            bound_is_actual.append(False)
        else:
            bc = cum_shares_at_year(bound_shares_list, yr)
            bv = bc * bound_price if bc > 0 else 0
            bound_is_actual.append(False)
        bound_values.append(round(bv))
        prev_bound = bv

    total_values = utils.compute_optiver_timeline(all_years, scenario)

    val_df = pd.DataFrame({
        "Year": all_years,
        "Free Shares (EUR)": free_values,
        "Bound Shares (EUR)": bound_values,
        "Total (EUR)": total_values,
    })

    cell_style_map = {
        "Free Shares (EUR)": {i: ("input" if free_is_actual[i] else "formula") for i in range(len(all_years))},
        "Bound Shares (EUR)": {i: ("input" if bound_is_actual[i] else "formula") for i in range(len(all_years))},
    }

    utils.render_aggrid_table(val_df, key="aggrid_optiver_valuations",
                              height=min(500, len(all_years) * 32 + 60),
                              numeric_cols=["Free Shares (EUR)", "Bound Shares (EUR)", "Total (EUR)"],
                              cell_style_map=cell_style_map)

    # Chart
    fig_val = go.Figure()
    actual_x = [all_years[i] for i in range(len(all_years)) if free_is_actual[i] or bound_is_actual[i]]
    actual_y = [total_values[i] for i in range(len(all_years)) if free_is_actual[i] or bound_is_actual[i]]
    proj_x = [all_years[i] for i in range(len(all_years)) if not (free_is_actual[i] or bound_is_actual[i]) and total_values[i] > 0]
    proj_y = [total_values[i] for i in range(len(all_years)) if not (free_is_actual[i] or bound_is_actual[i]) and total_values[i] > 0]
    if actual_x:
        fig_val.add_trace(go.Scatter(x=actual_x, y=actual_y, mode="lines+markers", name="Actual",
                                      line=dict(color="#f59e0b", width=3)))
    if proj_x:
        fig_val.add_trace(go.Scatter(x=proj_x, y=proj_y, mode="lines+markers", name="Projected",
                                      line=dict(color="#60a5fa", width=2, dash="dot")))
    fig_val.update_layout(template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
                          xaxis_title="Year", yaxis_title="Value (EUR)",
                          yaxis=dict(tickformat=",.0f"), title=f"Optiver Valuation ({scenario})")
    st.plotly_chart(fig_val, use_container_width=True)

    # Year-end override editor
    st.subheader("Enter Year-End Actual Values")
    st.caption("Enter actual year-end total value for Free and Bound shares separately. "
               "These override the projection formula. Set to 0 to clear.")
    override_years = list(range(start_year, utils.CURRENT_YEAR + 1))
    override_rows_data = []
    for yr in override_years:
        yr_str = str(yr)
        override_rows_data.append({
            "Year": yr,
            "Free (EUR)": free_yev.get(yr_str, 0),
            "Bound (EUR)": bound_yev.get(yr_str, 0),
        })
    override_df = pd.DataFrame(override_rows_data)
    st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter your values below</p>', unsafe_allow_html=True)
    st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
    edited_overrides = st.data_editor(override_df, use_container_width=True, hide_index=True,
        column_config={
            "Free (EUR)": st.column_config.NumberColumn(format="€%.0f"),
            "Bound (EUR)": st.column_config.NumberColumn(format="€%.0f"),
        },
        disabled=["Year"], key="optiver_override_editor")
    edited_overrides = utils.process_math_in_df(edited_overrides, ["Free (EUR)", "Bound (EUR)"], editor_key="optiver_year_end_overrides")

st.divider()

# Scenario appreciation
st.subheader("Scenario Appreciation")
scen_ap = data.get("scenario_appreciation", {})
c1, c2, c3, c4 = st.columns(4)
new_sa = {
    "super_bear": c1.number_input("Super Bear %", value=float(scen_ap.get("super_bear", 0)), step=0.5),
    "bear": c2.number_input("Bear %", value=float(scen_ap.get("bear", 5)), step=0.5),
    "base": c3.number_input("Base %", value=float(scen_ap.get("base", 10)), step=0.5),
    "bull": c4.number_input("Bull %", value=float(scen_ap.get("bull", 18)), step=0.5),
}

if st.button("💾 Save Optiver Data", type="primary"):
    free_rows = []
    for _, row in edited_free.iterrows():
        if pd.notna(row.get("year")):
            free_rows.append({"id": utils.new_id(), "year": int(row["year"]),
                              "shares_added": float(row.get("shares_added", 0) or 0),
                              "invested_amount": float(row.get("invested_amount", 0) or 0)})
    bound_rows = []
    for _, row in edited_bound.iterrows():
        if pd.notna(row.get("year")):
            bound_rows.append({"id": utils.new_id(), "year": int(row["year"]),
                               "shares_added": float(row.get("shares_added", 0) or 0),
                               "invested_amount": float(row.get("invested_amount", 0) or 0)})
    div_rows = []
    for _, row in edited_divs.iterrows():
        if pd.notna(row.get("year")):
            div_rows.append({"id": utils.new_id(), "year": int(row["year"]),
                             "div_per_share": float(row.get("div_per_share", 0) or 0),
                             "shares_eligible": float(row.get("shares_eligible", 0) or 0),
                             "tax": float(row.get("tax", 0) or 0),
                             "net_dividend": float(row.get("net_dividend", 0) or 0)})

    # Save year-end overrides
    new_yev = {"free": {}, "bound": {}}
    for _, row in edited_overrides.iterrows():
        yr_str = str(int(row["Year"]))
        fv = float(row.get("Free (EUR)", 0) or 0)
        bv = float(row.get("Bound (EUR)", 0) or 0)
        if fv > 0:
            new_yev["free"][yr_str] = fv
        if bv > 0:
            new_yev["bound"][yr_str] = bv

    new_data = {
        "free_share_price": new_free_price,
        "bound_share_price": new_bound_price,
        "free_shares": free_rows,
        "bound_shares": bound_rows,
        "dividends": div_rows,
        "scenario_appreciation": new_sa,
        "year_end_values": new_yev,
    }
    utils.save_json(utils.DATA_DIR / "optiver.json", new_data)
    st.success("Saved!")
    st.rerun()
