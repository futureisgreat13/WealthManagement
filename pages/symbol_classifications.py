import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("🏷️ Symbol Classifications")
st.caption("Manage how IBKR symbols are classified into asset classes. "
           "Any symbol not listed here defaults to **Public Stock** (Equity) during import.")

# Load classifications
classifications = utils.load_json(utils.DATA_DIR / "symbol_classifications.json", {})

CATEGORIES = ["ETF", "REIT", "Precious Metal", "Bond"]

# Build dataframe
rows = [{"Symbol": sym, "Category": cat} for sym, cat in sorted(classifications.items())]
df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Symbol", "Category"])

# Summary
cols = st.columns(len(CATEGORIES) + 1)
cols[0].metric("Total", len(df))
for i, cat in enumerate(CATEGORIES):
    count = len([r for r in rows if r["Category"] == cat])
    cols[i + 1].metric(cat, count)

st.divider()

# Filter
filter_cat = st.selectbox("Filter by category", ["All"] + CATEGORIES, index=0)
if filter_cat != "All":
    display_df = df[df["Category"] == filter_cat].reset_index(drop=True)
else:
    display_df = df.copy()

st.markdown(f"**{len(display_df)} symbols** {'(filtered)' if filter_cat != 'All' else ''}")

edited = st.data_editor(
    display_df,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    column_config={
        "Symbol": st.column_config.TextColumn("Symbol", width="medium"),
        "Category": st.column_config.SelectboxColumn(
            "Category", options=CATEGORIES, required=True, width="medium"),
    },
    key="symbol_class_editor",
)

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("💾 Save Changes", type="primary"):
        # Merge edits back: if filtered, we only edited a subset
        new_classifications = {}
        if filter_cat != "All":
            # Keep non-filtered entries
            for sym, cat in classifications.items():
                if cat != filter_cat:
                    new_classifications[sym] = cat
        # Add edited entries
        for _, row in edited.iterrows():
            sym = str(row.get("Symbol", "")).strip()
            cat = str(row.get("Category", "")).strip()
            if sym and cat in CATEGORIES:
                new_classifications[sym] = cat
        # Sort and save
        new_classifications = dict(sorted(new_classifications.items()))
        utils.save_json(utils.DATA_DIR / "symbol_classifications.json", new_classifications)
        st.success(f"Saved {len(new_classifications)} symbol classifications!")
        st.rerun()

st.divider()
st.subheader("🔍 Auto-Verify")
st.caption("Check symbols against yfinance to detect potential misclassifications.")

verify_col1, verify_col2 = st.columns([1, 4])
with verify_col1:
    verify_count = st.number_input("Symbols to check", min_value=10, max_value=len(classifications), value=min(50, len(classifications)), step=10)
with verify_col2:
    if st.button("🔍 Verify Classifications", key="auto_verify"):
        mismatches = []
        progress = st.progress(0)
        items = list(classifications.items())[:verify_count]
        for i, (sym, current_cat) in enumerate(items):
            result = utils.verify_symbol_classification(sym)
            suggested = result["suggested"]
            # Map Public Stock to no-match (it's the default for unknowns)
            if suggested != "Public Stock" and suggested != current_cat:
                mismatches.append({"Symbol": sym, "Current": current_cat,
                                   "Suggested": suggested, "Confidence": result["confidence"],
                                   "Reason": result["reason"]})
            progress.progress((i + 1) / len(items))
        progress.empty()

        if mismatches:
            st.warning(f"⚠️ Found {len(mismatches)} potential misclassification(s):")
            mm_df = pd.DataFrame(mismatches)
            st.dataframe(mm_df, use_container_width=True, hide_index=True)
        else:
            st.success(f"✅ All {len(items)} checked symbols look correct!")

st.divider()
st.subheader("Quick Add")
st.caption("Quickly add multiple symbols to a category at once.")
with st.form("quick_add"):
    qa_cat = st.selectbox("Category", CATEGORIES)
    qa_symbols = st.text_input("Symbols (comma-separated)", placeholder="e.g. AAPL, MSFT, GOOG")
    if st.form_submit_button("Add"):
        if qa_symbols.strip():
            added = 0
            for sym in qa_symbols.split(","):
                sym = sym.strip().upper()
                if sym:
                    classifications[sym] = qa_cat
                    added += 1
            classifications = dict(sorted(classifications.items()))
            utils.save_json(utils.DATA_DIR / "symbol_classifications.json", classifications)
            st.success(f"Added {added} symbols as {qa_cat}")
            st.rerun()
