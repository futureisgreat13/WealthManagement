import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("🏭 Business")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)

items = utils.load_json(utils.DATA_DIR / "business.json", [])

active_biz = [b for b in items if b.get("status") == "Active"]

def business_value(b):
    if b.get("status") == "Active":
        return b.get("expected_annual_cashflow_eur", 0) * b.get("pe_multiple", 1)
    return 0

# Year-end value: use value_history for latest completed year
latest_yr = str(utils.CURRENT_YEAR - 1)
total_val = 0
missing_items = []
for b in active_biz:
    vh = b.get("value_history", {})
    val = vh.get(latest_yr, 0)
    if val <= 0:
        val = business_value(b)
        missing_items.append(b.get("name", "Unknown"))
    total_val += val
year_label = f" ({latest_yr} YE)"
total_cf = sum(b.get("expected_annual_cashflow_eur", 0) for b in active_biz)
missing_note = ""
if missing_items:
    missing_note = f' <span style="color:red">* {len(missing_items)} items without {latest_yr} valuation</span>'

c1, c2 = st.columns(2)
c1.metric(f"Total Business Value{year_label}", utils.fmt_eur(total_val))
c2.metric("Annual Cash Flow", utils.fmt_eur(total_cf))
if missing_note:
    st.markdown(missing_note, unsafe_allow_html=True)

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Positions", "Income History", "Edit", "Projection"])

with tab1:
    if items:
        rows = []
        for b in items:
            val = business_value(b)
            rows.append({
                "Name": b.get("name",""),
                "Started": b.get("year_started",""),
                "Annual CF (EUR)": utils.fmt_eur_short(b.get("expected_annual_cashflow_eur",0)),
                "P/E Multiple": b.get("pe_multiple",0),
                "Value (EUR)": utils.fmt_eur_short(val),
                "Bankruptcy Risk %": b.get("bankruptcy_risk_pct",0),
                "Depreciation %": b.get("depreciation_pct",0),
                "Floor Value (EUR)": utils.fmt_eur_short(b.get("floor_value_eur",0)),
                "Status": b.get("status","Active"),
            })
        df = pd.DataFrame(rows)
        utils.render_aggrid_table(df, key="aggrid_business_positions", height=300)
    else:
        st.info("No businesses yet. Add them in the Edit tab.")

with tab2:
    st.subheader("Actual Income per Year")
    st.caption("Enter actual annual income for each business. "
               "This feeds into Cash Flow. For future years without actuals, "
               "the expected_annual_cashflow_eur is used as projection.")

    # Build year range from earliest start to current + 10
    min_yr = min((b.get("year_started", utils.CURRENT_YEAR) for b in items), default=2020)
    all_years = list(range(min_yr, utils.CURRENT_YEAR + 11))

    for idx, b in enumerate(items):
        bname = b.get("name", f"Business #{idx}")
        st.markdown(f"#### {bname}")
        ih = b.get("income_history", {})
        yr_start = b.get("year_started", 2020)
        expected = b.get("expected_annual_cashflow_eur", 0)

        inc_rows = []
        for yr in all_years:
            if yr < yr_start + 1:
                continue  # No income before first full year
            actual = ih.get(str(yr), 0)
            inc_rows.append({
                "Year": yr,
                "Actual Income (EUR)": actual,
                "Expected (EUR)": expected,
                "Source": "Actual" if actual > 0 else "Expected",
            })

        if inc_rows:
            inc_df = pd.DataFrame(inc_rows)
            st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter your values below</p>', unsafe_allow_html=True)
            st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
            inc_df = utils.inject_formulas_for_edit(inc_df, f"business_income_{idx}", ["Actual Income (EUR)"])
            edited_inc = st.data_editor(
                inc_df, use_container_width=True, hide_index=True,
                column_config={
                    "Actual Income (EUR)": st.column_config.TextColumn("Actual Income (EUR)"),
                    "Expected (EUR)": st.column_config.TextColumn("Expected (EUR)"),
                },
                disabled=["Year", "Expected (EUR)", "Source"],
                key=f"biz_income_{idx}",
            )
            edited_inc = utils.process_math_in_df(edited_inc, ["Actual Income (EUR)"], editor_key=f"business_income_{idx}")

            if st.button(f"💾 Save Income for {bname}", key=f"save_biz_inc_{idx}"):
                new_ih = {}
                for _, row in edited_inc.iterrows():
                    val = float(row.get("Actual Income (EUR)", 0) or 0)
                    if val > 0:
                        new_ih[str(int(row["Year"]))] = val
                items[idx]["income_history"] = new_ih
                utils.save_json(utils.DATA_DIR / "business.json", items)
                st.success(f"Income history saved for {bname}!")
                st.rerun()

with tab3:
    st.subheader("Edit Businesses")
    edit_rows = [{
        "name": b.get("name",""),
        "year_started": b.get("year_started",2020),
        "initial_investment_eur": b.get("initial_investment_eur",0),
        "expected_annual_cashflow_eur": b.get("expected_annual_cashflow_eur",0),
        "bankruptcy_risk_pct": b.get("bankruptcy_risk_pct",0),
        "depreciation_pct": b.get("depreciation_pct",0),
        "floor_value_eur": b.get("floor_value_eur",0),
        "pe_multiple": b.get("pe_multiple",8),
        "status": b.get("status","Active"),
        "close_year": b.get("close_year",""),
    } for b in items]

    edit_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(
        columns=["name","year_started","initial_investment_eur","expected_annual_cashflow_eur",
                 "bankruptcy_risk_pct","depreciation_pct","floor_value_eur","pe_multiple","status","close_year"])
    st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter your values below</p>', unsafe_allow_html=True)
    st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
    edit_df = utils.inject_formulas_for_edit(edit_df, "business_positions", ["initial_investment_eur", "expected_annual_cashflow_eur", "bankruptcy_risk_pct", "depreciation_pct", "floor_value_eur", "pe_multiple"])
    edited = st.data_editor(edit_df, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "status": st.column_config.SelectboxColumn("Status", options=["Active","Closed","For Sale"]),
            "initial_investment_eur": st.column_config.TextColumn("initial_investment_eur"),
            "expected_annual_cashflow_eur": st.column_config.TextColumn("expected_annual_cashflow_eur"),
            "floor_value_eur": st.column_config.TextColumn("floor_value_eur"),
        })
    edited = utils.process_math_in_df(edited, ["initial_investment_eur", "expected_annual_cashflow_eur", "bankruptcy_risk_pct", "depreciation_pct", "floor_value_eur", "pe_multiple"], editor_key="business_positions")

    if st.button("💾 Save", type="primary"):
        new_items = []
        for j, (_, row) in enumerate(edited.iterrows()):
            if row.get("name"):
                orig = items[j] if j < len(items) else {}
                new_items.append({
                    "id": orig.get("id", utils.new_id()),
                    "name": row["name"],
                    "year_started": int(row.get("year_started",2020) or 2020),
                    "initial_investment_eur": float(row.get("initial_investment_eur",0) or 0),
                    "expected_annual_cashflow_eur": float(row.get("expected_annual_cashflow_eur",0) or 0),
                    "bankruptcy_risk_pct": float(row.get("bankruptcy_risk_pct",0) or 0),
                    "depreciation_pct": float(row.get("depreciation_pct",0) or 0),
                    "floor_value_eur": float(row.get("floor_value_eur",0) or 0),
                    "pe_multiple": float(row.get("pe_multiple",8) or 8),
                    "status": row.get("status","Active"),
                    "close_year": row.get("close_year") or None,
                    "income_history": orig.get("income_history", {}),
                })
        utils.save_json(utils.DATA_DIR / "business.json", new_items)
        st.success("Saved!")
        st.rerun()

with tab4:
    active_biz = [b for b in items if b.get("status") == "Active"]
    if active_biz:
        st.subheader("Business Value Projection")
        scenario = st.session_state.get("scenario", "Base")
        years = list(range(utils.CURRENT_YEAR, utils.CURRENT_YEAR + 11))
        total_vals = utils.compute_business_timeline(years, scenario)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=total_vals, mode="lines+markers",
                                  name="Total Business Value", line=dict(color="#4c8bf5", width=3),
                                  text=[utils.fmt_eur(v) for v in total_vals],
                                  hovertemplate="%{x}: %{text}"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
                          xaxis_title="Year", yaxis_title="Value (EUR)", title=f"Business Projection ({scenario})")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No active businesses to project.")
