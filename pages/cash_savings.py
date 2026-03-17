import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("💶 Cash & Savings")

items = utils.load_json(utils.DATA_DIR / "cash.json", [])
fx = utils.load_fx_rates()

# --- Metrics ---
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

st.divider()

# --- Editable Accounts ---
st.subheader("Accounts")
edit_rows = [{
    "name": c.get("name", ""), "bank": c.get("bank", ""),
    "currency": c.get("currency", "EUR"), "amount": c.get("amount", 0),
    "interest_rate_pct": c.get("interest_rate_pct", 0), "type": c.get("type", "Cash"),
} for c in items]

edit_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(
    columns=["name", "bank", "currency", "amount", "interest_rate_pct", "type"])
st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — supports math (e.g. =500*2, 1000/EURUSD)</p>', unsafe_allow_html=True)
edited = st.data_editor(edit_df, use_container_width=True, hide_index=True, num_rows="dynamic",
    column_config={
        "currency": st.column_config.SelectboxColumn("Currency", options=utils.CURRENCIES),
        "type": st.column_config.SelectboxColumn("Type", options=["Cash", "Cash Equivalent"]),
        "amount": st.column_config.NumberColumn(format="%.2f"),
    })
edited = utils.process_math_in_df(edited, ["amount", "interest_rate_pct"], editor_key="cash_savings_accounts")

if st.button("💾 Save", type="primary", key="cash_save"):
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
    st.success("Saved!")
    st.rerun()
