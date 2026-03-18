import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("💶 Cash & Savings")
utils.show_unsaved_warning()

items = utils.load_json(utils.DATA_DIR / "cash.json", [])
fx = utils.load_fx_rates()

# --- Metrics (always visible above tabs) ---
total_eur = sum(utils.to_eur(i.get("amount", 0), i.get("currency", "EUR"), fx) for i in items)
cash_items = [i for i in items if i.get("type") == "Cash"]
equiv_items = [i for i in items if i.get("type") == "Cash Equivalent"]
total_cash = sum(utils.to_eur(i.get("amount", 0), i.get("currency", "EUR"), fx) for i in cash_items)
total_equiv = sum(utils.to_eur(i.get("amount", 0), i.get("currency", "EUR"), fx) for i in equiv_items)
total_interest = sum(
    utils.to_eur(i.get("amount", 0), i.get("currency", "EUR"), fx) * i.get("interest_rate_pct", 0) / 100
    for i in items
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total", utils.fmt_eur(total_eur))
c2.metric("Cash", utils.fmt_eur(total_cash))
c3.metric("Cash Equivalents", utils.fmt_eur(total_equiv))
c4.metric("Annual Interest", utils.fmt_eur(total_interest))

# --- Tabs ---
tab1, tab2 = st.tabs(["Positions", "Edit"])

with tab1:
    if not items:
        st.info("No accounts yet. Add them in the Edit tab.")
    else:
        rows = []
        for c in items:
            amount_eur = utils.to_eur(c.get("amount", 0), c.get("currency", "EUR"), fx)
            annual_int = amount_eur * c.get("interest_rate_pct", 0) / 100
            rows.append({
                "Name": c.get("name", ""),
                "Bank": c.get("bank", ""),
                "Currency": c.get("currency", "EUR"),
                "Amount": c.get("amount", 0),
                "Amount (EUR)": amount_eur,
                "Interest Rate %": c.get("interest_rate_pct", 0),
                "Annual Interest (EUR)": annual_int,
                "Type": c.get("type", "Cash"),
            })
        df = pd.DataFrame(rows)
        utils.render_aggrid_table(df, key="aggrid_cash_positions", height=400)

with tab2:
    st.subheader("Edit Accounts")
    edit_rows = [{
        "name": c.get("name", ""), "bank": c.get("bank", ""),
        "currency": c.get("currency", "EUR"), "amount": c.get("amount", 0),
        "interest_rate_pct": c.get("interest_rate_pct", 0), "type": c.get("type", "Cash"),
    } for c in items]

    edit_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(
        columns=["name", "bank", "currency", "amount", "interest_rate_pct", "type"])
    st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
    edit_df = utils.inject_formulas_for_edit(edit_df, "cash_savings_accounts", ["amount", "interest_rate_pct"])
    _orig_cash_pos = edit_df.copy()
    edited = st.data_editor(edit_df, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "currency": st.column_config.SelectboxColumn("Currency", options=utils.CURRENCIES),
            "type": st.column_config.SelectboxColumn("Type", options=["Cash", "Cash Equivalent"]),
            "amount": st.column_config.TextColumn("amount"),
        })
    edited = utils.process_math_in_df(edited, ["amount", "interest_rate_pct"], editor_key="cash_savings_accounts")
    utils.track_unsaved_changes("cash_pos", _orig_cash_pos, edited)

    if st.button("💾 Save", type="primary", key="cash_save"):
        deleted = utils.check_deleted_items(items, edited, name_col="name")
        if not deleted:
            st.session_state["_pending_save_cash_positions"] = True
        else:
            st.session_state["_delete_confirm_cash_positions"] = deleted
        st.rerun()

    # Handle pending save / delete confirmation (outside button block for Streamlit rerun compatibility)
    save_result = utils.handle_save_with_delete_confirmation("cash_positions", [])
    if save_result == "save":
        new_items = []
        for j, (_, row) in enumerate(edited.iterrows()):
            if row.get("name"):
                orig = items[j] if j < len(items) else {}
                new_items.append({
                    "id": orig.get("id", utils.new_id()),
                    "name": row["name"], "bank": row.get("bank", ""),
                    "currency": row.get("currency", "EUR"),
                    "amount": float(row.get("amount", 0) or 0),
                    "interest_rate_pct": float(row.get("interest_rate_pct", 0) or 0),
                    "type": row.get("type", "Cash"),
                })
        utils.save_json(utils.DATA_DIR / "cash.json", new_items)
        utils.clear_unsaved("cash_pos")
        st.success("Saved!")
        st.rerun()
    elif save_result == "cancelled":
        st.rerun()
