import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("📉 Debt")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)

items = utils.load_json(utils.DATA_DIR / "debt.json", [])

total_debt = sum(i.get("outstanding_balance_eur",0) * i.get("pro_rata_pct",100) / 100 for i in items)
annual_payments = sum(i.get("annual_payment_eur",0) for i in items)

c1, c2 = st.columns(2)
c1.metric("Total Outstanding Debt", f"-{utils.fmt_eur(total_debt)}")
c2.metric("Annual Payments", utils.fmt_eur(annual_payments))

st.divider()

if items:
    rows = []
    for d in items:
        balance = d.get("outstanding_balance_eur",0) * d.get("pro_rata_pct",100) / 100
        rows.append({
            "Name": d.get("name",""),
            "Year Taken": d.get("year_taken",""),
            "Original Amount (EUR)": utils.fmt_eur_short(d.get("original_amount_eur",0)),
            "Outstanding (EUR)": utils.fmt_eur_short(balance),
            "Interest Rate %": d.get("interest_rate_pct",0),
            "Type": d.get("type","Fixed"),
            "Pro Rata %": d.get("pro_rata_pct",100),
            "Annual Payment (EUR)": utils.fmt_eur_short(d.get("annual_payment_eur",0)),
        })
    df = pd.DataFrame(rows)
    utils.render_aggrid_table(df, key="aggrid_debt_positions", height=300)

tab_edit, tab_val = st.tabs(["Edit Debt", "Valuations"])

with tab_val:
    st.caption("🟡 Yellow = user-entered actual balance. ⚪ White = projected from annual payments.")
    base_year = utils.get_base_year() or (utils.CURRENT_YEAR - 2)
    val_years = list(range(base_year, base_year + 11))
    active_debt = [d for d in items if d.get("outstanding_balance_eur", 0) > 0 or d.get("year_taken", 9999) >= base_year]
    if active_debt:
        val_rows = []
        for d in active_debt:
            row = {"Name": d.get("name", "")}
            vh = d.get("value_history", {})
            balance = d.get("outstanding_balance_eur", 0)
            annual = d.get("annual_payment_eur", 0)
            rate = d.get("interest_rate_pct", 0) / 100
            for yr in val_years:
                yr_str = str(yr)
                if yr_str in vh:
                    row[yr_str] = vh[yr_str]
                else:
                    # Project: use last known balance
                    prev_yr_str = str(yr - 1)
                    if prev_yr_str in row and isinstance(row[prev_yr_str], (int, float)):
                        prev_bal = row[prev_yr_str]
                    else:
                        prev_bal = balance
                    interest = prev_bal * rate
                    principal = max(annual - interest, 0)
                    row[yr_str] = max(prev_bal - principal, 0)
            val_rows.append(row)

        val_df = pd.DataFrame(val_rows)
        col_config = {"Name": st.column_config.TextColumn(disabled=True)}
        for yr in val_years:
            col_config[str(yr)] = st.column_config.NumberColumn(format="€%.0f")
        val_df = utils.inject_formulas_for_edit(val_df, "debt_valuations", [str(yr) for yr in val_years])
        edited_val = st.data_editor(val_df, width="stretch", hide_index=True, column_config=col_config)
        edited_val = utils.process_math_in_df(edited_val, [str(yr) for yr in val_years], editor_key="debt_valuations")

        if st.button("💾 Save Valuations", type="primary", key="save_debt_val"):
            for idx, d in enumerate(active_debt):
                if idx < len(edited_val):
                    erow = edited_val.iloc[idx]
                    vh = d.get("value_history", {})
                    for yr in val_years:
                        yr_str = str(yr)
                        new_val = float(erow.get(yr_str, 0) or 0)
                        # Only save if user changed from projected value (treat as actual)
                        orig_vh = d.get("value_history", {})
                        if yr_str in orig_vh or new_val != val_rows[idx].get(yr_str, -1):
                            vh[yr_str] = new_val
                    d["value_history"] = vh
                    # Update outstanding_balance to latest confirmed year
                    for yr in sorted(val_years, reverse=True):
                        yr_str = str(yr)
                        if yr_str in vh and yr < utils.CURRENT_YEAR:
                            d["outstanding_balance_eur"] = vh[yr_str]
                            break
            utils.save_json(utils.DATA_DIR / "debt.json", items)
            st.success("Valuations saved!")
            st.rerun()
    else:
        st.info("No active debt items to show valuations for.")

with tab_edit:
    edit_rows = [{
        "name": d.get("name",""), "year_taken": d.get("year_taken",2020),
        "original_amount_eur": d.get("original_amount_eur",0),
        "interest_rate_pct": d.get("interest_rate_pct",0),
        "type": d.get("type","Fixed"),
        "pro_rata_pct": d.get("pro_rata_pct",100),
        "outstanding_balance_eur": d.get("outstanding_balance_eur",0),
        "annual_payment_eur": d.get("annual_payment_eur",0),
    } for d in items]

    edit_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(columns=["name","year_taken","original_amount_eur","interest_rate_pct","type","pro_rata_pct","outstanding_balance_eur","annual_payment_eur"])
    st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter your values below</p>', unsafe_allow_html=True)
    st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
    edit_df = utils.inject_formulas_for_edit(edit_df, "debt_positions", ["original_amount_eur", "outstanding_balance_eur", "annual_payment_eur", "interest_rate_pct", "pro_rata_pct"])
    edited = st.data_editor(edit_df, width="stretch", hide_index=True, num_rows="dynamic",
        column_config={
            "type": st.column_config.SelectboxColumn("Type", options=["Fixed","Variable","Interest Only"]),
            "original_amount_eur": st.column_config.NumberColumn(format="€%.0f"),
            "outstanding_balance_eur": st.column_config.NumberColumn(format="€%.0f"),
            "annual_payment_eur": st.column_config.NumberColumn(format="€%.0f"),
        })
    edited = utils.process_math_in_df(edited, ["original_amount_eur", "outstanding_balance_eur", "annual_payment_eur", "interest_rate_pct", "pro_rata_pct"], editor_key="debt_positions")

    if st.button("💾 Save Debt", type="primary"):
        new_items = []
        for j, (_, row) in enumerate(edited.iterrows()):
            if row.get("name"):
                orig = items[j] if j < len(items) else {}
                new_items.append({
                    "id": orig.get("id", utils.new_id()),
                    "name": row["name"],
                    "year_taken": int(row.get("year_taken",2020) or 2020),
                    "original_amount_eur": float(row.get("original_amount_eur",0) or 0),
                    "interest_rate_pct": float(row.get("interest_rate_pct",0) or 0),
                    "type": row.get("type","Fixed"),
                    "pro_rata_pct": float(row.get("pro_rata_pct",100) or 100),
                    "outstanding_balance_eur": float(row.get("outstanding_balance_eur",0) or 0),
                    "annual_payment_eur": float(row.get("annual_payment_eur",0) or 0),
                })
        utils.save_json(utils.DATA_DIR / "debt.json", new_items)
        st.success("Saved!")
        st.rerun()

    # Amortization chart
    if items:
        st.subheader("Debt Amortization")
        years = utils.get_projection_years(10)
        fig = go.Figure()
        colors_list = ["#ff4444","#ff9944","#ffff44","#44ff88","#44ffff","#4444ff"]
        for idx, d in enumerate(items):
            balance = d.get("outstanding_balance_eur",0) * d.get("pro_rata_pct",100) / 100
            annual = d.get("annual_payment_eur",0)
            rate = d.get("interest_rate_pct",0) / 100
            balances = [balance]
            for _ in range(10):
                interest = balances[-1] * rate
                principal = max(annual - interest, 0)
                new_bal = max(balances[-1] - principal, 0)
                balances.append(new_bal)
            fig.add_trace(go.Scatter(x=years, y=balances, mode="lines+markers",
                                      name=d.get("name",""), line=dict(color=colors_list[idx % len(colors_list)])))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
                          xaxis_title="Year", yaxis_title="Outstanding Balance (EUR)", title="Debt Amortization")
        st.plotly_chart(fig, width="stretch")
