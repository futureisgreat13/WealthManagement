import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("🏭 Business")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)
utils.render_year_end_alert("Business")

items = utils.load_json(utils.DATA_DIR / "business.json", [])
active_biz = [b for b in items if b.get("status") == "Active"]

# ── Positions ─────────────────────────────────────────────────────────
st.subheader("Positions")

edit_rows = [{
    "name": b.get("name", ""),
    "year_started": b.get("year_started", 2020),
    "initial_investment_eur": b.get("initial_investment_eur", 0),
    "expected_annual_cashflow_eur": b.get("expected_annual_cashflow_eur", 0),
    "pe_multiple": b.get("pe_multiple", 5),
    "bankruptcy_risk_pct": b.get("bankruptcy_risk_pct", 0),
    "depreciation_pct": b.get("depreciation_pct", 0),
    "floor_value_eur": b.get("floor_value_eur", 0),
    "status": b.get("status", "Active"),
    "close_year": b.get("close_year", ""),
    "exit_sale_value_eur": b.get("exit_sale_value_eur", 0),
} for b in items]

edit_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(
    columns=["name", "year_started", "initial_investment_eur", "expected_annual_cashflow_eur",
             "pe_multiple", "bankruptcy_risk_pct", "depreciation_pct", "floor_value_eur",
             "status", "close_year", "exit_sale_value_eur"])

numeric_text_cols = ["initial_investment_eur", "expected_annual_cashflow_eur", "pe_multiple",
                     "bankruptcy_risk_pct", "depreciation_pct", "floor_value_eur", "exit_sale_value_eur"]

st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter your values below</p>', unsafe_allow_html=True)
st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
edit_df = utils.inject_formulas_for_edit(edit_df, "business_positions", numeric_text_cols)
edited = st.data_editor(edit_df, use_container_width=True, hide_index=True, num_rows="dynamic",
    column_config={
        "status": st.column_config.SelectboxColumn("Status", options=["Active", "Closed", "For Sale"]),
        "initial_investment_eur": st.column_config.TextColumn("initial_investment_eur"),
        "expected_annual_cashflow_eur": st.column_config.TextColumn("expected_annual_cashflow_eur"),
        "floor_value_eur": st.column_config.TextColumn("floor_value_eur"),
        "pe_multiple": st.column_config.TextColumn("pe_multiple"),
        "exit_sale_value_eur": st.column_config.TextColumn("exit_sale_value_eur"),
    })
edited = utils.process_math_in_df(edited, numeric_text_cols, editor_key="business_positions")

if st.button("💾 Save Positions", type="primary"):
    deleted = utils.check_deleted_items(items, edited, name_col="name")
    if not deleted:
        st.session_state["_pending_save_business_positions"] = True
    else:
        st.session_state["_delete_confirm_business_positions"] = deleted
    st.rerun()

# Handle pending save / delete confirmation (outside button block for Streamlit rerun compatibility)
save_result = utils.handle_save_with_delete_confirmation("business_positions", [])
if save_result == "save":
    new_items = []
    for j, (_, row) in enumerate(edited.iterrows()):
        if row.get("name"):
            orig = items[j] if j < len(items) else {}
            new_items.append({
                "id": orig.get("id", utils.new_id()),
                "name": row["name"],
                "year_started": int(row.get("year_started", 2020) or 2020),
                "initial_investment_eur": float(row.get("initial_investment_eur", 0) or 0),
                "expected_annual_cashflow_eur": float(row.get("expected_annual_cashflow_eur", 0) or 0),
                "pe_multiple": float(row.get("pe_multiple", 5) or 5),
                "bankruptcy_risk_pct": float(row.get("bankruptcy_risk_pct", 0) or 0),
                "depreciation_pct": float(row.get("depreciation_pct", 0) or 0),
                "floor_value_eur": float(row.get("floor_value_eur", 0) or 0),
                "status": row.get("status", "Active"),
                "close_year": int(row["close_year"]) if row.get("close_year") else None,
                "exit_sale_value_eur": float(row.get("exit_sale_value_eur", 0) or 0),
                "income_history": orig.get("income_history", {}),
                "value_history": orig.get("value_history", {}),
            })
    utils.save_json(utils.DATA_DIR / "business.json", new_items)
    st.success("Saved!")
    st.rerun()
elif save_result == "cancelled":
    st.rerun()

st.divider()

# ── Valuation ─────────────────────────────────────────────────────────
st.subheader("Valuation")
st.caption("Formula: (1 − Bankruptcy Risk%) × (max(Depreciated Investment, Floor Value) + P/E × Income). "
           "Override any cell to store a manual valuation.")

if items:
    min_yr = min((b.get("year_started", utils.CURRENT_YEAR) for b in items), default=utils.CURRENT_YEAR)
    val_years = list(range(min_yr, utils.CURRENT_YEAR + 6))
    yr_cols = [str(y) for y in val_years]

    val_rows = []
    col_source_map = {}
    for yr_col in yr_cols:
        col_source_map[yr_col] = {}

    for idx, b in enumerate(items):
        row = {"Business": b.get("name", f"#{idx}")}
        vh = b.get("value_history", {})
        for yr_col in yr_cols:
            yr = int(yr_col)
            formula_val = utils.compute_business_value_for_year(b, yr)
            override = vh.get(yr_col)
            if override is not None and override > 0:
                row[yr_col] = override
                col_source_map[yr_col][idx] = "input"
            else:
                row[yr_col] = formula_val if formula_val > 0 else None
        val_rows.append(row)

    # Total row
    total_row = {"Business": "Total"}
    for yr_col in yr_cols:
        total_row[yr_col] = sum(r.get(yr_col, 0) or 0 for r in val_rows)
    val_rows.append(total_row)

    val_df = pd.DataFrame(val_rows)
    bg_style_map, cell_style_map = utils.build_valuation_style_maps(col_source_map)

    val_result = utils.render_editable_aggrid_table(
        val_df, key="aggrid_business_valuation", height=min(300, 80 + 35 * len(val_rows)),
        editable_cols=yr_cols,
        numeric_cols=yr_cols,
        highlight_total_row=True,
        bg_style_map=bg_style_map,
        cell_style_map=cell_style_map,
        editor_key="business_valuation",
    )

    if st.button("💾 Save Valuation", key="save_biz_val"):
        edited_val = val_result.data if hasattr(val_result, 'data') else val_result
        for idx, b in enumerate(items):
            if idx >= len(edited_val) - 1:  # Skip total row
                break
            vh = b.get("value_history", {})
            for yr_col in yr_cols:
                yr = int(yr_col)
                try:
                    cell_val = float(edited_val.iloc[idx][yr_col] or 0)
                except (ValueError, TypeError):
                    cell_val = 0
                formula_val = utils.compute_business_value_for_year(b, yr)
                if cell_val > 0 and abs(cell_val - formula_val) > 0.01:
                    vh[yr_col] = cell_val
                else:
                    vh.pop(yr_col, None)
            items[idx]["value_history"] = vh
        utils.save_json(utils.DATA_DIR / "business.json", items)
        st.success("Valuation saved!")
        st.rerun()
else:
    st.info("No businesses yet. Add them in the Positions section above.")

st.divider()

# ── Income ────────────────────────────────────────────────────────────
st.subheader("Income")
st.caption("Default = Expected Annual CF until overridden. Yellow cells = user-entered actuals.")

if items:
    min_income_yr = min((b.get("year_started", utils.CURRENT_YEAR) + 1 for b in items), default=utils.CURRENT_YEAR)
    income_years = list(range(min_income_yr, utils.CURRENT_YEAR + 6))
    inc_yr_cols = [str(y) for y in income_years]

    inc_rows = []
    inc_source_map = {}
    for yr_col in inc_yr_cols:
        inc_source_map[yr_col] = {}

    for idx, b in enumerate(items):
        row = {"Business": b.get("name", f"#{idx}")}
        ih = b.get("income_history", {})
        yr_start = b.get("year_started", 2020)
        expected = b.get("expected_annual_cashflow_eur", 0)
        close_yr = b.get("close_year") or 9999

        for yr_col in inc_yr_cols:
            yr = int(yr_col)
            if yr < yr_start + 1 or yr > close_yr:
                row[yr_col] = None
            else:
                actual = ih.get(yr_col, 0)
                if actual > 0:
                    row[yr_col] = actual
                    inc_source_map[yr_col][idx] = "input"
                else:
                    row[yr_col] = expected
        inc_rows.append(row)

    # Total row
    total_row = {"Business": "Total"}
    for yr_col in inc_yr_cols:
        total_row[yr_col] = sum(r.get(yr_col, 0) or 0 for r in inc_rows)
    inc_rows.append(total_row)

    inc_df = pd.DataFrame(inc_rows)
    inc_bg_map, inc_cell_map = utils.build_valuation_style_maps(inc_source_map)

    inc_result = utils.render_editable_aggrid_table(
        inc_df, key="aggrid_business_income", height=min(300, 80 + 35 * len(inc_rows)),
        editable_cols=inc_yr_cols,
        numeric_cols=inc_yr_cols,
        highlight_total_row=True,
        bg_style_map=inc_bg_map,
        cell_style_map=inc_cell_map,
        editor_key="business_income",
    )

    if st.button("💾 Save Income", key="save_biz_inc"):
        edited_inc = inc_result.data if hasattr(inc_result, 'data') else inc_result
        for idx, b in enumerate(items):
            if idx >= len(edited_inc) - 1:  # Skip total row
                break
            ih = {}
            yr_start = b.get("year_started", 2020)
            expected = b.get("expected_annual_cashflow_eur", 0)
            for yr_col in inc_yr_cols:
                yr = int(yr_col)
                if yr < yr_start + 1:
                    continue
                try:
                    cell_val = float(edited_inc.iloc[idx][yr_col] or 0)
                except (ValueError, TypeError):
                    cell_val = 0
                # Only store if different from expected (user override)
                if cell_val > 0 and abs(cell_val - expected) > 0.01:
                    ih[yr_col] = cell_val
            # Preserve any income_history entries outside the displayed range
            old_ih = b.get("income_history", {})
            for k, v in old_ih.items():
                if k not in inc_yr_cols:
                    ih[k] = v
            items[idx]["income_history"] = ih
        utils.save_json(utils.DATA_DIR / "business.json", items)
        st.success("Income saved!")
        st.rerun()
else:
    st.info("No businesses yet. Add them in the Positions section above.")
