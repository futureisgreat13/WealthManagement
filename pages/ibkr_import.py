import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("📥 IBKR Import")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}</style>', unsafe_allow_html=True)
st.caption("Upload two IBKR CSV exports to import positions, dividends, and net capital flows. "
           "Symbols are classified using the Symbol Classifications database.")

# --- Step 0: Year Selection ---
st.subheader("📅 Import Year")
import_year = st.number_input("Which year are these CSVs for?", min_value=2020,
                               max_value=utils.CURRENT_YEAR, value=utils.CURRENT_YEAR - 1,
                               step=1, help="The year-end these CSVs represent")

# --- Step 1: Upload CSVs ---
st.divider()
st.subheader("📂 Upload CSVs")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**CSV 1: Positions & Dividends**")
    st.caption("Contains open positions + dividend payments per symbol. "
               "Download from IBKR: Reports → Activity → Custom → select Positions & Dividends.")
    uploaded_pos = st.file_uploader("Positions & Dividends CSV", type=["csv"], key="pos_csv")

with col2:
    st.markdown("**CSV 2: Transactions (Trades)**")
    st.caption("Contains all buy/sell transactions for the period. "
               "Download from IBKR: Reports → Activity → Custom → select Trades.")
    uploaded_tx = st.file_uploader("Transactions CSV", type=["csv"], key="tx_csv")

# --- Process uploads ---
if uploaded_pos and uploaded_tx:
    try:
        pos_content = uploaded_pos.read().decode("utf-8")
        tx_content = uploaded_tx.read().decode("utf-8")

        # Validate dates in transactions match selected year
        tx_years = set()
        for line in tx_content.strip().split("\n")[1:]:
            parts = line.split(",")
            for p in parts:
                p = p.strip().strip('"')
                if len(p) == 8 and p.isdigit():
                    tx_years.add(p[:4])
                    break
        if tx_years and str(import_year) not in tx_years:
            st.warning(f"⚠️ The transactions CSV contains dates from year(s) **{', '.join(sorted(tx_years))}** "
                       f"but you selected import year **{import_year}**. Please verify this is correct.")

        # Run the import computation
        result = utils.compute_ibkr_import(pos_content, tx_content, import_year)

        # --- Show unclassified symbols ---
        if result["unclassified"]:
            st.warning(f"⚠️ **{len(result['unclassified'])} symbols** not in classification database "
                       f"(defaulting to Public Stock): {', '.join(result['unclassified'])}. "
                       f"Add them via the Symbol Classifications page if needed.")

        # --- Positions by Asset Class ---
        st.divider()
        st.subheader(f"📊 Positions Summary ({import_year} Year-End)")

        # Valuation metrics
        val = result["valuations_by_class"]
        total_val = sum(val.values())
        metric_cols = st.columns(min(len(val) + 1, 6))
        metric_cols[0].metric("Total Value", utils.fmt_eur_short(total_val))
        for i, (ac, v) in enumerate(sorted(val.items())):
            if i + 1 < len(metric_cols):
                metric_cols[i + 1].metric(ac, utils.fmt_eur_short(v))

        # Positions tables per asset class
        for ac, positions in sorted(result["positions_by_class"].items()):
            with st.expander(f"**{ac}** — {len(positions)} positions, {utils.fmt_eur_short(sum(p['value_eur'] for p in positions))}",
                            expanded=False):
                pos_df = pd.DataFrame([{
                    "Symbol": p["symbol"],
                    "Category": p["category"],
                    "Currency": p["currency"],
                    "Quantity": round(p["quantity"], 2),
                    "Price": round(p["mark_price"], 2),
                    "Value (EUR)": round(p["value_eur"]),
                    "Cost (EUR)": round(p["cost_eur"]),
                } for p in sorted(positions, key=lambda x: -x["value_eur"])])
                utils.render_aggrid_table(pos_df, key=f"ibkr_pos_{ac.replace(' ', '_')}",
                                          height=min(500, len(pos_df) * 32 + 60),
                                          numeric_cols=["Value (EUR)", "Cost (EUR)", "Quantity", "Price"])

        # --- Dividends ---
        st.divider()
        st.subheader(f"💰 Dividends ({import_year})")

        div_by_class = result["dividends_by_class"]
        total_div = sum(div_by_class.values())
        if total_div > 0:
            div_cols = st.columns(min(len(div_by_class) + 1, 6))
            div_cols[0].metric("Total Dividends", utils.fmt_eur_short(total_div))
            for i, (ac, d) in enumerate(sorted(div_by_class.items())):
                if i + 1 < len(div_cols):
                    div_cols[i + 1].metric(ac, utils.fmt_eur_short(d))

            # Per-symbol dividend table
            with st.expander("Dividends by Symbol", expanded=False):
                div_rows = [{
                    "Symbol": sym,
                    "Category": info["category"],
                    "Asset Class": info["asset_class"],
                    "Dividends (EUR)": info["amount_eur"],
                } for sym, info in sorted(result["dividends_by_symbol"].items(),
                                          key=lambda x: -x[1]["amount_eur"])]
                div_df = pd.DataFrame(div_rows)
                utils.render_aggrid_table(div_df, key="ibkr_dividends",
                                          height=min(600, len(div_df) * 32 + 60),
                                          numeric_cols=["Dividends (EUR)"])
        else:
            st.info("No dividend data found in the positions CSV.")

        # --- Net Capital Flows ---
        st.divider()
        st.subheader(f"📈 Net Capital Flows ({import_year})")
        st.caption("Positive = net bought (cash invested), Negative = net sold (cash returned). "
                   "FX trades excluded.")

        net_cap = result["net_capital_by_class"]
        if net_cap:
            cap_rows = [{
                "Asset Class": ac,
                "Net Capital (EUR)": amt,
                "Direction": "Invested" if amt > 0 else "Returned",
            } for ac, amt in sorted(net_cap.items())]
            cap_df = pd.DataFrame(cap_rows)
            utils.render_aggrid_table(cap_df, key="ibkr_net_capital",
                                      height=min(300, len(cap_df) * 36 + 60),
                                      numeric_cols=["Net Capital (EUR)"])
        else:
            st.info("No transactions found (excluding FX trades).")

        # --- Import Button ---
        st.divider()
        st.subheader("✅ Apply Import")
        st.caption("This will update: year-end valuations, actual dividends in cash flow, "
                   "and net capital flows per asset class.")

        if st.button("🚀 Import All Data", type="primary", key="apply_ibkr"):
            summary = utils.apply_ibkr_import(result)
            yr = summary["year"]

            st.success(f"✅ Successfully imported {yr} IBKR data!")
            st.markdown(f"""
            **{yr} Year-End Valuations Updated:**
            - Equity: {utils.fmt_eur_short(summary['equity_val'])}
            - ETF: {utils.fmt_eur_short(summary['etf_val'])}
            - REITs: {utils.fmt_eur_short(summary['reit_val'])}
            - Precious Metals: {utils.fmt_eur_short(summary['metals_val'])}
            - Bonds: {utils.fmt_eur_short(summary['bonds_val'])}

            **Dividends:** {', '.join(f"{ac}: {utils.fmt_eur_short(v)}" for ac, v in summary['dividends'].items())}

            **Net Capital:** {', '.join(f"{ac}: {utils.fmt_eur_short(v)}" for ac, v in summary['net_capital'].items())}
            """)
            st.balloons()

    except Exception as e:
        st.error(f"Error processing files: {e}")
        import traceback
        st.code(traceback.format_exc())

elif uploaded_pos or uploaded_tx:
    st.info("Please upload **both** CSVs to proceed with the import.")

else:
    st.info("Upload both IBKR CSVs to begin importing.")
    st.markdown("""
    **How to download from IBKR:**

    **CSV 1 — Positions & Dividends:**
    1. Go to Reports → Flex Queries (or Activity → Custom Statements)
    2. Include: Open Positions, Cash Report, Dividends
    3. Export as CSV

    **CSV 2 — Transactions:**
    1. Go to Reports → Flex Queries (or Activity → Custom Statements)
    2. Include: Trades
    3. Export as CSV

    **What gets imported:**
    - 📊 **Year-end valuations** per asset class (Equity, ETF, REIT, Precious Metals, Bonds)
    - 💰 **Dividends** per asset class for cash flow actuals
    - 📈 **Net capital flows** (buys - sells) per asset class
    """)

# --- Show existing stored data ---
st.divider()
st.subheader("Stored IBKR Capital Flows")
st.caption("Previously imported net capital flows. These override assumptions in Future Valuations.")

existing_flows = utils.load_ibkr_capital_flows()
if existing_flows:
    edit_rows = []
    for ac, yr_data in sorted(existing_flows.items()):
        for yr, amt in sorted(yr_data.items()):
            edit_rows.append({"Asset Class": ac, "Year": yr, "Net Capital (EUR)": amt})
    if edit_rows:
        edit_df = pd.DataFrame(edit_rows)
        edit_df = utils.inject_formulas_for_edit(edit_df, "ibkr_capital", ["Net Capital (EUR)"])
        edited = st.data_editor(edit_df, use_container_width=True, hide_index=True,
            num_rows="dynamic",
            column_config={
                "Net Capital (EUR)": st.column_config.NumberColumn(format="€%.0f"),
                "Asset Class": st.column_config.SelectboxColumn(
                    options=["Equity", "REIT", "Precious Metals", "Bond"]),
            },
            key="ibkr_flows_editor")
        edited = utils.process_math_in_df(edited, ["Net Capital (EUR)"], editor_key="ibkr_capital")

        if st.button("💾 Update Stored Flows", type="primary", key="update_ibkr_flows"):
            new_flows = {}
            for _, row in edited.iterrows():
                ac = row.get("Asset Class", "")
                yr = str(row.get("Year", ""))
                amt = float(row.get("Net Capital (EUR)", 0) or 0)
                if ac and yr:
                    new_flows.setdefault(ac, {})[yr] = round(amt)
            utils.save_ibkr_capital_flows(new_flows)
            st.success("IBKR flows updated!")
            st.rerun()
else:
    st.info("No IBKR capital flows stored yet. Import CSVs above.")

# --- Raw IBKR Database Viewer ---
st.divider()
st.subheader("📦 Raw IBKR Database")
st.caption("Complete record of all imported IBKR data, stored centrally for reference.")

ibkr_db = utils.load_ibkr_database()
if ibkr_db:
    db_years = sorted(ibkr_db.keys(), reverse=True)
    selected_year = st.selectbox("View import year", db_years, key="ibkr_db_year")
    yr_data = ibkr_db.get(selected_year, {})

    if yr_data:
        st.info(f"Imported on: {yr_data.get('imported_at', 'unknown')}")

        # Summary metrics
        summary = yr_data.get("summary", {})
        val_by_class = yr_data.get("valuations_by_class", {})
        if val_by_class:
            metric_cols = st.columns(min(len(val_by_class) + 1, 6))
            total_val = sum(val_by_class.values())
            metric_cols[0].metric("Total Value", utils.fmt_eur_short(total_val))
            for i, (ac, v) in enumerate(sorted(val_by_class.items())):
                if i + 1 < len(metric_cols):
                    metric_cols[i + 1].metric(ac, utils.fmt_eur_short(v))

        # Positions per class
        pos_by_class = yr_data.get("positions_by_class", {})
        for ac, positions in sorted(pos_by_class.items()):
            with st.expander(f"**{ac}** — {len(positions)} positions"):
                pos_df = pd.DataFrame([{
                    "Symbol": p["symbol"], "Category": p["category"],
                    "Currency": p["currency"], "Qty": round(p["quantity"], 2),
                    "Price": round(p["mark_price"], 2),
                    "Value (EUR)": round(p["value_eur"]),
                    "Cost (EUR)": round(p["cost_eur"]),
                } for p in sorted(positions, key=lambda x: -x["value_eur"])])
                utils.render_aggrid_table(pos_df, key=f"ibkr_db_pos_{ac}_{selected_year}",
                                          height=min(500, len(pos_df) * 32 + 60),
                                          numeric_cols=["Value (EUR)", "Cost (EUR)", "Qty", "Price"])

        # Dividends
        div_by_class = yr_data.get("dividends_by_class", {})
        if div_by_class and sum(div_by_class.values()) > 0:
            with st.expander(f"**Dividends** — {utils.fmt_eur_short(sum(div_by_class.values()))} total"):
                div_by_sym = yr_data.get("dividends_by_symbol", {})
                if div_by_sym:
                    div_rows = [{"Symbol": s, "Category": info["category"],
                                 "Asset Class": info["asset_class"],
                                 "Dividends (EUR)": round(info["amount_eur"])}
                                for s, info in sorted(div_by_sym.items(), key=lambda x: -x[1]["amount_eur"])]
                    div_df = pd.DataFrame(div_rows)
                    utils.render_aggrid_table(div_df, key=f"ibkr_db_div_{selected_year}",
                                              height=min(500, len(div_df) * 32 + 60),
                                              numeric_cols=["Dividends (EUR)"])

        # Net Capital
        net_cap = yr_data.get("net_capital_by_class", {})
        if net_cap:
            with st.expander(f"**Net Capital Flows**"):
                cap_rows = [{"Asset Class": ac, "Net Capital (EUR)": round(amt),
                             "Direction": "Invested" if amt > 0 else "Returned"}
                            for ac, amt in sorted(net_cap.items())]
                cap_df = pd.DataFrame(cap_rows)
                utils.render_aggrid_table(cap_df, key=f"ibkr_db_cap_{selected_year}",
                                          height=min(300, len(cap_df) * 36 + 60),
                                          numeric_cols=["Net Capital (EUR)"])
else:
    st.info("No IBKR data imported yet. Upload CSVs above to build the database.")
