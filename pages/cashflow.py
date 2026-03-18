import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

utils.inject_bloomberg_css()
st.title("Cash Flow")

fx = utils.load_fx_rates()
data = utils.load_json(utils.DATA_DIR / "cashflow.json", {})
all_years = sorted([str(y) for y in data.get("years", [])], key=lambda x: int(x))
income = data.get("income", {})
expenses = data.get("expenses", {})
actuals = data.get("actual_cash_by_year", {})

MANUAL_INCOME = {"Optiver Bonus", "Optiver Dividends", "Salary", "Debt Inflow"}
MANUAL_EXPENSE = {"Wealth Tax", "Life Expenses"}

cf_results = utils.compute_full_cashflow(data)

# ── Year filter: default last 3 actuals + future ──
cutoff = str(utils.CURRENT_YEAR - 3)
default_years = [y for y in all_years if y >= cutoff]
show_all = st.checkbox(f"Show all years (from {all_years[0]})", value=False, key="cf_show_all")
years = all_years if show_all else default_years

# ── KPI METRICS ──
current_yr = str(utils.CURRENT_YEAR)
cur = cf_results.get(current_yr, {})
c1, c2, c3, c4 = st.columns(4)
c1.metric("OLD CASH", utils.fmt_eur(cur.get("old_cash", 0)), f"Start {current_yr}")
c2.metric("INCOME", utils.fmt_eur(cur.get("total_income", 0)), current_yr)
c3.metric("EXPENSES", utils.fmt_eur(cur.get("total_expenses", 0)), current_yr)
c4.metric("CASH LEFT", utils.fmt_eur(cur.get("cash_left", 0)), f"End {current_yr}")

# ── COMPACT CHART ──
fig = go.Figure()
fig.add_trace(go.Bar(
    x=all_years, y=[cf_results[y]["total_income"] for y in all_years],
    name="Income", marker_color=utils.C_GREEN, opacity=0.5))
fig.add_trace(go.Bar(
    x=all_years, y=[-cf_results[y]["total_expenses"] for y in all_years],
    name="Expenses", marker_color=utils.C_RED, opacity=0.5))
fig.add_trace(go.Scatter(
    x=all_years, y=[cf_results[y]["cash_left"] for y in all_years],
    name="Cash Left", mode="lines+markers",
    line=dict(color=utils.C_ORANGE, width=2), marker=dict(size=4),
    hovertemplate="%{x}: €%{y:,.0f}<extra>Cash Left</extra>",
))
actual_years = [y for y in all_years if actuals.get(y, 0) > 0]
if actual_years:
    fig.add_trace(go.Scatter(
        x=actual_years, y=[actuals[y] for y in actual_years],
        name="Actual", mode="markers",
        marker=dict(size=8, color=utils.C_GOLD, symbol="diamond"),
    ))
fig.update_layout(**utils.bloomberg_chart_layout(height=220, barmode="overlay"))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# =============================================================================
# HEATMAP TABLE — styled with green/red intensity
# =============================================================================
st.subheader("Detail")

# Build all rows
display_rows = []
row_is_manual = []
row_categories = []

# --- Old Cash ---
old_row = {"Category": "OLD CASH"}
for y in years:
    old_row[y] = round(cf_results[y]["old_cash"])
display_rows.append(old_row)
row_is_manual.append(False)
row_categories.append(("computed", "old_cash"))

# --- INCOME SECTION ---
income_total_by_year = {y: 0 for y in years}
for label in income.keys():
    is_manual = label in MANUAL_INCOME
    row = {"Category": label}
    for y in years:
        v = cf_results[y]["computed_income"].get(label, 0)
        row[y] = round(v)
        income_total_by_year[y] += v
    display_rows.append(row)
    row_is_manual.append(is_manual)
    row_categories.append(("income", label))

inc_sub = {"Category": "TOTAL INCOME"}
for y in years:
    inc_sub[y] = round(income_total_by_year[y])
display_rows.append(inc_sub)
row_is_manual.append(False)
row_categories.append(("computed", "total_income"))

# --- EXPENSE & INVESTMENT SECTION ---
expense_total_by_year = {y: 0 for y in years}
for label in expenses.keys():
    is_manual = label in MANUAL_EXPENSE
    row = {"Category": label}
    for y in years:
        expense_val = cf_results[y]["computed_expenses"].get(label, 0)
        row[y] = round(-expense_val)
        expense_total_by_year[y] += expense_val
    display_rows.append(row)
    row_is_manual.append(is_manual)
    row_categories.append(("expense", label))

exp_sub = {"Category": "TOTAL EXPENSES"}
for y in years:
    exp_sub[y] = round(-expense_total_by_year[y])
display_rows.append(exp_sub)
row_is_manual.append(False)
row_categories.append(("computed", "total_expenses"))

net_row = {"Category": "NET CASH FLOW"}
for y in years:
    net_row[y] = round(cf_results[y]["net_cf"])
display_rows.append(net_row)
row_is_manual.append(False)
row_categories.append(("computed", "net_cf"))

cash_row = {"Category": "CASH LEFT"}
for y in years:
    cash_row[y] = round(cf_results[y]["cash_left"])
display_rows.append(cash_row)
row_is_manual.append(False)
row_categories.append(("computed", "cash_left"))

actual_row = {"Category": "ACTUAL CASH"}
for y in years:
    actual_row[y] = round(actuals.get(y, 0))
display_rows.append(actual_row)
row_is_manual.append(True)
row_categories.append(("actual_cash", "actual_cash"))

# --- Styled heatmap display ---
display_df = pd.DataFrame(display_rows)

# Find max absolute value for heatmap scaling
all_vals = []
for row in display_rows:
    for y in years:
        v = row.get(y, 0)
        if v != 0:
            all_vals.append(abs(v))
max_val = max(all_vals) if all_vals else 1

def heatmap_style(row):
    idx = display_df.index.get_loc(row.name)
    cat_str = str(row.get("Category", ""))
    n = len(row)

    # Summary rows: orange text, dark bg
    summary_cats = {"OLD CASH", "TOTAL INCOME", "TOTAL EXPENSES", "NET CASH FLOW", "CASH LEFT"}
    if cat_str in summary_cats:
        return [f"background-color: {utils.BG_HEADER}; color: {utils.C_ORANGE}; font-weight: 600; font-size: 11px"] * n

    # Manual rows: gold border-left indicator
    if idx < len(row_is_manual) and row_is_manual[idx]:
        styles = [f"color: {utils.C_GOLD}; font-size: 11px"]  # Category col
        for y in years:
            v = row.get(y, 0)
            styles.append(f"color: {utils.C_GOLD}; font-size: 11px")
        return styles[:n]

    # Tab-driven rows: green/red heatmap
    styles = [f"color: {utils.C_LABEL}; font-size: 11px"]  # Category col
    for y in years:
        v = row.get(y, 0)
        if v > 0:
            intensity = min(0.35, (abs(v) / max_val) * 0.5)
            styles.append(f"background-color: rgba(0, 255, 136, {intensity:.2f}); color: {utils.C_GREEN}; font-size: 11px")
        elif v < 0:
            intensity = min(0.35, (abs(v) / max_val) * 0.5)
            styles.append(f"background-color: rgba(255, 68, 68, {intensity:.2f}); color: {utils.C_RED}; font-size: 11px")
        else:
            styles.append(f"color: #333; font-size: 11px")
    return styles[:n]

styled = display_df.style.apply(heatmap_style, axis=1).format(
    {y: "{:,.0f}" for y in years})

n_rows = len(display_rows)
table_height = min(800, max(300, n_rows * 28 + 40))
st.dataframe(styled, use_container_width=True, hide_index=True, height=table_height,
    column_config={
        "Category": st.column_config.TextColumn(width="small"),
        **{y: st.column_config.TextColumn() for y in years},
    })

# =============================================================================
# EDITABLE SECTION — Only manual rows
# =============================================================================
with st.expander("Edit Manual Values", expanded=False):
    st.caption("Gold rows from table above. Math expressions supported (500*2, 1000/EURUSD).")

    edit_rows = []
    edit_row_mapping = []

    for label in income.keys():
        if label not in MANUAL_INCOME:
            continue
        row = {"Category": label}
        for y in years:
            row[y] = round(cf_results[y]["computed_income"].get(label, 0))
        edit_rows.append(row)
        edit_row_mapping.append(("income", label))

    for label in expenses.keys():
        if label not in MANUAL_EXPENSE:
            continue
        row = {"Category": label}
        for y in years:
            row[y] = round(cf_results[y]["computed_expenses"].get(label, 0))
        edit_rows.append(row)
        edit_row_mapping.append(("expense", label))

    act_row = {"Category": "Actual Cash"}
    for y in years:
        act_row[y] = round(actuals.get(y, 0))
    edit_rows.append(act_row)
    edit_row_mapping.append(("actual_cash", "actual_cash"))

    edit_df = pd.DataFrame(edit_rows)
    edited = st.data_editor(edit_df, use_container_width=True, hide_index=True,
        column_config={
            "Category": st.column_config.TextColumn(width="small"),
            **{y: st.column_config.TextColumn(y) for y in years},
        },
        disabled=["Category"],
        key="cashflow_unified_editor")
    edited = utils.process_math_in_df(edited, years, editor_key="cashflow_income")

    if st.button("Save Changes", type="primary", key="cashflow_save"):
        for i, (_, row) in enumerate(edited.iterrows()):
            section, cat = edit_row_mapping[i]
            if section == "income":
                existing = income.get(cat, {})
                for y in years:
                    existing[y] = float(row.get(y, 0) or 0)
                income[cat] = existing
            elif section == "expense":
                existing = expenses.get(cat, {})
                for y in years:
                    existing[y] = float(row.get(y, 0) or 0)
                expenses[cat] = existing
            elif section == "actual_cash":
                new_actuals = {}
                for y in years:
                    val = float(row.get(y, 0) or 0)
                    if val > 0:
                        new_actuals[y] = val
                data["actual_cash_by_year"] = new_actuals
        data["income"] = income
        data["expenses"] = expenses
        utils.save_json(utils.DATA_DIR / "cashflow.json", data)
        st.success("Saved!")
        st.rerun()

with st.expander("Data Sources"):
    st.markdown(f"""
<span style="color:{utils.C_LABEL};font-size:0.8rem">

| Category | Source |
|----------|--------|
| Equity, REITs, PM, Bonds | Valuation tab > Net Capital |
| Private Equity | PE: investments − exits (net) |
| Real Estate | RE: investments − exits (net) |
| Funds | Capital call schedule |
| Business, Debt Payment | Tab data |
| Dividends | Positions × yield or IBKR |
| **Gold rows** | **Manual entry (editor above)** |

</span>
""", unsafe_allow_html=True)
