import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("📉 Debt")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)
utils.render_year_end_alert("Debt")
utils.show_unsaved_warning()

items = utils.load_json(utils.DATA_DIR / "debt.json", [])

total_debt = sum(i.get("outstanding_balance_eur", 0) for i in items)
annual_payments = sum(i.get("annual_payment_eur", 0) for i in items)

c1, c2 = st.columns(2)
c1.metric("Total Outstanding Debt", f"-{utils.fmt_eur(total_debt)}")
c2.metric("Annual Payments", utils.fmt_eur(annual_payments))

st.divider()

# ── Positions (single editable table) ──────────────────────────
st.subheader("Positions")
st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")

edit_rows = [{
    "name": d.get("name", ""),
    "year_taken": d.get("year_taken", 2020),
    "original_amount_eur": d.get("original_amount_eur", 0),
    "interest_rate_pct": d.get("interest_rate_pct", 0),
    "outstanding_balance_eur": d.get("outstanding_balance_eur", 0),
    "annual_payment_eur": d.get("annual_payment_eur", 0),
} for d in items]

edit_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(
    columns=["name", "year_taken", "original_amount_eur", "interest_rate_pct",
             "outstanding_balance_eur", "annual_payment_eur"])

numeric_cols = ["year_taken", "original_amount_eur", "outstanding_balance_eur", "annual_payment_eur", "interest_rate_pct"]
edit_df = utils.inject_formulas_for_edit(edit_df, "debt_positions", numeric_cols)
orig_edit_df = edit_df.copy()

edited = st.data_editor(edit_df, width="stretch", hide_index=True, num_rows="dynamic",
    column_config={
        "name": st.column_config.TextColumn("Name"),
        "year_taken": st.column_config.TextColumn("Year Taken"),
        "original_amount_eur": st.column_config.TextColumn("Original Amount (EUR)"),
        "interest_rate_pct": st.column_config.TextColumn("Interest Rate %"),
        "outstanding_balance_eur": st.column_config.TextColumn("Outstanding (EUR)"),
        "annual_payment_eur": st.column_config.TextColumn("Annual Payment (EUR)"),
    })
edited = utils.process_math_in_df(edited, numeric_cols, editor_key="debt_positions")
utils.track_unsaved_changes("debt_positions", orig_edit_df, edited)

if st.button("💾 Save Debt", type="primary"):
    deleted = utils.check_deleted_items(items, edited, name_col="name")
    if not deleted:
        st.session_state["_pending_save_debt_positions"] = True
    else:
        st.session_state["_delete_confirm_debt_positions"] = deleted
    st.rerun()

# Handle pending save / delete confirmation (outside button block for Streamlit rerun compatibility)
save_result = utils.handle_save_with_delete_confirmation("debt_positions", [])
if save_result == "save":
    new_items = []
    for j, (_, row) in enumerate(edited.iterrows()):
        if row.get("name") and str(row["name"]).strip():
            orig = items[j] if j < len(items) else {}
            new_item = {
                "id": orig.get("id", utils.new_id()),
                "name": str(row["name"]).strip(),
                "year_taken": int(float(row.get("year_taken", 2020) or 2020)),
                "original_amount_eur": float(row.get("original_amount_eur", 0) or 0),
                "interest_rate_pct": float(row.get("interest_rate_pct", 0) or 0),
                "outstanding_balance_eur": float(row.get("outstanding_balance_eur", 0) or 0),
                "annual_payment_eur": float(row.get("annual_payment_eur", 0) or 0),
            }
            # Preserve existing histories
            if "value_history" in orig:
                new_item["value_history"] = orig["value_history"]
            if "payment_history" in orig:
                new_item["payment_history"] = orig["payment_history"]
            new_items.append(new_item)
    utils.save_json(utils.DATA_DIR / "debt.json", new_items)
    utils.clear_unsaved("debt_positions")
    st.toast("✅ Debt positions saved!")
    st.rerun()

st.divider()

# ── Debt Payments (per-year grid) ──────────────────────────────
st.subheader("Debt Payments")
st.caption("🟡 Yellow = actual payment entered. ⚪ White = expected (from annual payment). Payments flow into cashflow as cash out.")

active_debt = [d for d in items if d.get("outstanding_balance_eur", 0) > 0
               or d.get("annual_payment_eur", 0) > 0
               or d.get("original_amount_eur", 0) > 0]

if active_debt:
    earliest_year = min(d.get("year_taken", utils.CURRENT_YEAR) for d in active_debt)
    payment_years = list(range(earliest_year, utils.CURRENT_YEAR + 11))
    pay_year_strs = [str(yr) for yr in payment_years]

    pay_rows = []
    pay_source_map = {yr_str: {} for yr_str in pay_year_strs}

    for idx, d in enumerate(active_debt):
        row = {"Name": d.get("name", "")}
        ph = d.get("payment_history", {})
        annual = d.get("annual_payment_eur", 0)
        year_taken = d.get("year_taken", utils.CURRENT_YEAR)

        for yr in payment_years:
            yr_str = str(yr)
            if yr < year_taken:
                row[yr_str] = 0
            elif yr_str in ph:
                row[yr_str] = float(ph[yr_str])
                pay_source_map[yr_str][idx] = "input"
            else:
                row[yr_str] = annual
                pay_source_map[yr_str][idx] = "formula"
        pay_rows.append(row)

    pay_df = pd.DataFrame(pay_rows)

    # Build style maps for yellow/white coloring
    bg_map, cell_map = utils.build_valuation_style_maps(pay_source_map)

    pay_grid_result = utils.render_editable_aggrid_table(
        pay_df, key="debt_payments_grid",
        editable_cols=pay_year_strs,
        numeric_cols=pay_year_strs,
        bg_style_map=bg_map,
        cell_style_map=cell_map,
        editor_key="debt_payments",
    )
    edited_pay_df = pay_grid_result.data if hasattr(pay_grid_result, 'data') else pay_df

    if st.button("💾 Save Payments", type="primary", key="save_debt_payments"):
        result_df = edited_pay_df
        changes_made = 0

        for idx, d in enumerate(active_debt):
            if idx >= len(result_df):
                break
            erow = result_df.iloc[idx]
            ph = d.get("payment_history", {})
            year_taken = d.get("year_taken", utils.CURRENT_YEAR)

            for yr in payment_years:
                yr_str = str(yr)
                if yr < year_taken:
                    continue
                try:
                    new_val = float(erow[yr_str] if yr_str in erow.index else 0)
                except (ValueError, TypeError):
                    new_val = 0
                # Compare with original DataFrame to detect any edit
                try:
                    orig_val = float(pay_df.iloc[idx][yr_str] if yr_str in pay_df.columns else 0)
                except (ValueError, TypeError, IndexError):
                    orig_val = 0
                if abs(new_val - orig_val) > 0.01 or yr_str in ph:
                    ph[yr_str] = new_val
                    changes_made += 1
            d["payment_history"] = ph

        utils.save_json(utils.DATA_DIR / "debt.json", items)
        st.toast(f"✅ Payments saved! ({changes_made} values stored)")
        st.rerun()
else:
    st.info("No active debt items.")

st.divider()

# ── Valuations / Outstanding Balance ───────────────────────────
st.subheader("Valuations")
st.caption("🟡 Yellow = user-entered year-end balance. ⚪ White = projected: prev_balance × (1 + rate) − payment. "
           "User-entered values override formula and become the base for subsequent projections.")

all_debt = [d for d in items if d.get("name")]
if all_debt:
    earliest_year = min(d.get("year_taken", utils.CURRENT_YEAR) for d in all_debt)
    val_years = list(range(earliest_year, utils.CURRENT_YEAR + 11))
    val_year_strs = [str(yr) for yr in val_years]

    val_rows = []
    val_source_map = {yr_str: {} for yr_str in val_year_strs}

    for idx, d in enumerate(all_debt):
        row = {"Name": d.get("name", "")}
        vh = d.get("value_history", {})
        ph = d.get("payment_history", {})
        balance = d.get("outstanding_balance_eur", 0)
        annual = d.get("annual_payment_eur", 0)
        rate = d.get("interest_rate_pct", 0) / 100
        year_taken = d.get("year_taken", utils.CURRENT_YEAR)
        orig_amount = d.get("original_amount_eur", 0)

        prev_bal = orig_amount  # Start from original amount

        for yr in val_years:
            yr_str = str(yr)
            if yr < year_taken:
                row[yr_str] = 0
                val_source_map[yr_str][idx] = "formula"
                continue

            if yr_str in vh and vh[yr_str] is not None:
                row[yr_str] = float(vh[yr_str])
                val_source_map[yr_str][idx] = "input"
                prev_bal = float(vh[yr_str])
            else:
                # Project: prev_balance * (1 + rate) - payment
                payment = float(ph.get(yr_str, annual))
                projected = prev_bal * (1 + rate) - payment
                projected = max(projected, 0) if projected == projected else 0  # NaN safety
                row[yr_str] = round(projected, 0)
                val_source_map[yr_str][idx] = "formula"
                prev_bal = projected

        val_rows.append(row)

    val_df = pd.DataFrame(val_rows)

    # Build style maps for yellow/white coloring
    val_bg_map, val_cell_map = utils.build_valuation_style_maps(val_source_map)

    val_grid_result = utils.render_editable_aggrid_table(
        val_df, key="debt_valuations_grid",
        editable_cols=val_year_strs,
        numeric_cols=val_year_strs,
        bg_style_map=val_bg_map,
        cell_style_map=val_cell_map,
        editor_key="debt_valuations",
    )
    edited_val_df = val_grid_result.data if hasattr(val_grid_result, 'data') else val_df

    if st.button("💾 Save Valuations", type="primary", key="save_debt_val"):
        edited_val = edited_val_df
        changes_made = 0

        for idx, d in enumerate(all_debt):
            if idx >= len(edited_val):
                break
            erow = edited_val.iloc[idx]
            vh = d.get("value_history", {})
            year_taken = d.get("year_taken", utils.CURRENT_YEAR)

            # First pass: detect which years were edited
            edited_years = set()
            for yr in val_years:
                yr_str = str(yr)
                if yr < year_taken:
                    continue
                try:
                    new_val = float(erow[yr_str] if yr_str in erow.index else 0)
                except (ValueError, TypeError):
                    new_val = 0
                # Compare with original DataFrame value to detect any edit
                try:
                    orig_val = float(val_df.iloc[idx][yr_str] if yr_str in val_df.columns else 0)
                except (ValueError, TypeError, IndexError):
                    orig_val = -1
                if yr_str in vh or abs(new_val - orig_val) > 0.01:
                    vh[yr_str] = new_val
                    edited_years.add(yr)
                    changes_made += 1

            # Second pass: if a year was edited, clear stale future value_history
            # entries that weren't also edited (so formula takes over from new base)
            if edited_years:
                latest_edited = max(edited_years)
                stale_keys = [k for k in list(vh.keys())
                              if int(k) > latest_edited and int(k) not in edited_years]
                for k in stale_keys:
                    del vh[k]

            d["value_history"] = vh

            # Update outstanding_balance to latest confirmed year-end
            for yr in sorted(val_years, reverse=True):
                yr_str = str(yr)
                if yr_str in vh and yr < utils.CURRENT_YEAR:
                    d["outstanding_balance_eur"] = vh[yr_str]
                    break

        utils.save_json(utils.DATA_DIR / "debt.json", items)
        st.toast(f"✅ Valuations saved! ({changes_made} values stored)")
        st.rerun()
else:
    st.info("No debt items to show valuations for.")

st.divider()

# ── Amortization Chart ─────────────────────────────────────────
if items:
    st.subheader("Debt Amortization")
    active_for_chart = [d for d in items if d.get("outstanding_balance_eur", 0) > 0]
    if active_for_chart:
        years = utils.get_projection_years(10)
        fig = go.Figure()
        colors_list = ["#ff4444", "#ff9944", "#ffff44", "#44ff88", "#44ffff", "#4444ff"]
        for idx, d in enumerate(active_for_chart):
            balance = d.get("outstanding_balance_eur", 0)
            annual = d.get("annual_payment_eur", 0)
            rate = d.get("interest_rate_pct", 0) / 100
            balances = [balance]
            for _ in range(10):
                interest = balances[-1] * rate
                principal = max(annual - interest, 0)
                new_bal = max(balances[-1] - principal, 0)
                balances.append(new_bal)
            fig.add_trace(go.Scatter(x=years, y=balances, mode="lines+markers",
                                      name=d.get("name", ""),
                                      line=dict(color=colors_list[idx % len(colors_list)])))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
                          xaxis_title="Year", yaxis_title="Outstanding Balance (EUR)", title="Debt Amortization")
        st.plotly_chart(fig, use_container_width=True)
