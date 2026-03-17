import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("📖 Rules & Documentation")
st.caption("How the dashboard works. All rules and formulas documented here.")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["App Rules", "Notes (Editable)"])

with tab1:
    st.markdown("""
## General Principles

- **Year** = year-end valuation. All values represent end-of-year positions.
- **Base currency** = EUR. All values converted via configurable FX rates.
- **Number format**: K = thousands (e.g., €100K), M = millions (e.g., €1.5M), B = billions.
- **Last actual data**: 2024 is the last year with confirmed year-end data.
  2025+ are projections until the user enters actual year-end values.
- **Display tables**: AG-Grid with cell range selection. Select cells → status bar shows sum/avg/count.
- **Color coding**:
  - 🟡 **Gold text** = user-entered actual value (anchor/override)
  - **White text** = formula-computed value
  - 🟢 **Green border** on editable areas = manual input fields
- **Scenario system**: Super Bear / Bear / Base / Bull — applies across all projections.

---

## Overview Dashboard

- **Net Worth** = sum of all asset class totals (including negative Debt).
- **Liquid Assets**: Equity, REITs, Bonds, Precious Metals, Cash.
- **Illiquid Assets**: Private Equity, Real Estate, Funds, Business, Debt.
- **10yr Projection** uses `get_portfolio_projection_v2()` which combines all asset class models.
- **Available to Invest** = current year income − non-investment expenses (Life, Tax, Debt).
- **Annual Liquid Income** = dividends + coupons + interest from liquid assets.
- **Asset Values by Year grid**: Historical (2020-2024) from records, 2025+ from scenario projection.
- **Ideal Allocation**: User sets target % per asset class. Gap analysis suggests rebalancing amounts.

---

## Public Stocks, ETFs, REITs & Precious Metals

- All positions stored in `public_stocks.json` with a `type` field:
  **Equity**, **ETF**, **REIT**, or **Precious Metals**.
- Values stored as pre-computed EUR totals (`cost_eur`, `value_eur`, `net_div_eur`).
- Each page filters by type and shows relevant positions.
- **Future Valuations** formula:
  ```
  V(N) = V(N-1) × (1 + expected_return) + new_capital_invested(N)
  ```
  - `new_capital_invested(N)`: IBKR data first → cashflow expenses → investment plan.
  - Expected returns: configurable per class in FX & Settings (default 10%).
  - Scenario multipliers applied to base return: Super Bear ×0.5, Bear ×0.7, Base ×1.0, Bull ×1.5.
- **Year-end override**: Enter actual year-end total value per asset class.
  Stored in `asset_value_history.json`. Future years auto-recalculate from latest actual.
- **Auto-detect base year**: System finds latest year with actual data, projects from there.
- **IBKR integration**: When IBKR capital flows are stored, `new_capital` uses IBKR data
  (marked 🟡 gold) instead of assumptions. This overrides investment plan values.
- **Price refresh**: yfinance integration updates current prices for all positions.

---

## Private Equity Model

- **value_history**: Tracks year-end valuations per investment.
  - **Pre-2023**: Invested capital held constant (no historical data available).
  - **2023/2024**: Imported from Excel (actual year-end valuations).
  - **2025 investments**: Value = invested amount (no appreciation until year-end).
- **Future valuation formula** (year-over-year):
  ```
  V(N) = V(N-1) × (1 + IRR) × success_probability
  ```
  Where IRR and probability are per-investment parameters.
- **year_invested** is respected: no value appears before investment year.
  E.g., Anduril invested in 2025 shows 0 for 2024.
- **Base year**: Projections start from 2024 (last actual data).
  When user adds 2025 year-end data, 2026+ auto-recalculates from 2025 anchor.
- **Overrides**: value_history entries take precedence over formula calculations.
  Optiver items have intentional overrides for 2025/2026 as anchors.
- **success_probability**: Derived from "Chance to 0" assessment.
  - `success_probability = (1 - chance_to_0) × 100`
  - Default = **0%** if not specified (conservative — assumes total loss).
- **Statuses**: Active (in portfolio), Exited (realized), Written Off (total loss).
- **Scenario adjustments**:
  - Super Bear: IRR × 0.5, Probability × 0.5
  - Bear: IRR × 0.7, Probability × 0.75
  - Base: as-is
  - Bull: IRR × 1.3, Probability capped at 100%

---

## Real Estate Model

- Same structure as Private Equity (value_history, IRR, probability).
- **Formula**: `V(N) = V(N-1) × (1 + IRR) × success_probability`
- Additional fields: **mortgage_total**, **mortgage_outstanding**, **annual_rental**.
- **Net Equity** = Current Value − Mortgage Outstanding.
- Rental income feeds into Cash Flow as Business Income equivalent.
- **year_invested** respected: properties don't show value before purchase year.
- Year-end actual values input works the same as PE (enter → becomes anchor).

---

## Funds Model

- **Capital calls**: Entered as % of total commitment per year.
  - Each fund has its own schedule — must be manually entered.
  - Color indicators: 🟢 95-100% total planned, 🔴 >100%, 🟡 <95%.
  - User enters actual called EUR at year-end.
- **Valuation formula**:
  ```
  V(N) = V(N-1) × (1 + IRR) + new_capital_called(N)
  ```
- **Base year**: 2024 (last actual data). Projections start from 2024 values.
- **Expected exit year**: After exit, fund value drops to 0 (distributed as cash).
  - `None` / Open = fund compounds indefinitely (no defined exit).
- **year_invested** respected: funds don't show value before investment year.
- **Year-end update**: User overrides total NAV → future recalculates from that anchor.
- **Scenario**: IRR multiplied by Super Bear 0.5×, Bear 0.7×, Base 1.0×, Bull 1.3×.

---

## Business Model

- **Value** = Expected Annual Cash Flow × P/E Multiple.
- **year_started**: Business doesn't contribute to projection before start year.
- **Income History**: Actual income per year feeds into Cash Flow.
  For future years without actuals, `expected_annual_cashflow_eur` is used.
- **Projection**: Value grows at business return rate (configurable in assumptions).
- **Statuses**: Active, Closed, For Sale.

---

## Cash Flow

- **Formula-based for future years (2025+)**: Auto-computed from individual asset tabs.
- **Historical (2020-2024)**: Stored values used as-is (known actuals).
- **Unified table**: Single table showing income AND expenses/investments.

### Auto-pulled categories (future years):
| Category | Source |
|----------|--------|
| Equity Dividends | Sum of `net_div_eur` from public_stocks.json (type=Equity+ETF) |
| REITs Dividends | Sum of `net_div_eur` from public_stocks.json (type=REIT) |
| PE Dividends | Sum of `annual_dividend_eur` from active PE items |
| Business Income | From business.json income_history or expected cashflow |
| Funds (expense) | From capital call schedules in funds.json |
| Business (expense) | From business.json initial investments |
| Debt Payment | From debt.json annual payments |

### Manual categories (always from cashflow.json):
- Optiver Bonus, Optiver Dividends, Salary, Life Expenses, Optiver Shares, Wealth Tax

### Investment rows (NET display):
- Each asset class row shows **NET**: `sale_amount − purchase_amount`
  - **Negative** = more invested than sold (cash out)
  - **Positive** = more sold than invested (cash in)
- Asset sales are netted within each asset class row (no separate "Asset Sale" income)
- `asset_sale_breakdown` in cashflow.json maps historical sales to specific asset classes.

### Cash carry-forward:
- **Old Cash** = previous year's actual cash (if entered) or calculated Cash Left.
- **Cash Left** = Old Cash + Total Income − Total Expenses.
- **actual_cash_by_year**: User inputs actual year-end cash balance.
  - This **overrides** calculated Cash Left for next year's carry-forward.
  - `0` = no entry (model uses calculated). Use `1` if actual balance is zero.

---

## IBKR Import

- Upload Interactive Brokers Activity Statement (CSV).
- **Open Positions**: Auto-categorizes as Stocks/ETFs, REITs, Bonds, Precious Metals.
  Merges with existing data (matches by ticker, updates quantity/price).
- **Net Capital Flows** (from Trades section):
  - Computes net bought/sold per asset class per year.
  - Positive = net bought (cash out), Negative = net sold (cash in).
  - Stored in `ibkr_capital_flows.json`.
  - Overrides investment plan assumptions in Future Valuations (marked 🟡 gold).
  - Also updates `asset_sale_breakdown` in cashflow.json for negative flows (sales).

---

## Scenarios

Applied to projections across all asset classes:

| Scenario | PE IRR × | PE Prob × | RE IRR × | Liquid Return × | Funds IRR × |
|----------|----------|-----------|----------|-----------------|-------------|
| Super Bear | 0.5× | 0.5× | 0.5× | varies* | 0.5× |
| Bear | 0.7× | 0.75× | 0.7× | varies* | 0.7× |
| Base | 1.0× | 1.0× | 1.0× | varies* | 1.0× |
| Bull | 1.3× | 1.0× | 1.3× | varies* | 1.3× |

*Liquid asset returns are set per-asset-class per-scenario in FX & Settings (assumptions.json).

---

## Year-End Process

1. **Import IBKR statement**: Upload CSV → import positions + capital flows.
2. **Refresh stock prices**: yfinance refresh on Stocks, REITs, Metals pages.
3. **Update PE/RE/Funds valuations**: Enter year-end values in Future Valuations tab.
   - These become 🟡 gold anchors; future years auto-recalculate from them.
4. **Update liquid asset totals**: Enter year-end value in each asset's Future Valuations tab.
5. **Update actual cash**: Enter actual cash balance in Cash Flow → Actual Cash tab.
6. **Review cash flow**: Check unified table, adjust any manual overrides needed.
7. **Auto-recalculation**: All projections automatically recalculate from new anchors.
8. The model for next year starts from updated reality, not old projections.

---

## FX & Settings

- **FX Rates**: EUR/USD, EUR/INR, EUR/GBP, EUR/HKD, EUR/JPY, EUR/CAD, EUR/AUD, EUR/CHF.
- **Scenario Return Assumptions**: Per asset class, per scenario (Super Bear / Bear / Base / Bull).
- **Liquid Asset Returns**: Base rates for Equity, REIT, Precious Metals (with scenario multipliers).
- **Dividend Yields**: Expected yields for projecting future dividend income.
- **Actual Dividend History**: Enter actual dividends received per class per year.

---

## Wealth Tax

- Dutch Box 3 system.
- Estimated at ~1.2% above €114K exemption (couple).
- Formula: `(total_taxable − €114K − primary_home) × 1.2%`
- Primary home excluded from taxable base.
- Rate approximation: ~6.17% deemed return × 36% tax rate ≈ 1.2% effective.

---

## Investment Plan

- Shows current allocation vs target % for all asset classes.
- Gap analysis: difference between current and target allocation.
- Planned annual investment per asset class (stored in `investment_plan.json`).
- Feeds into Future Valuations as default `new_capital` when no IBKR data or override exists.

---

## Data Files

| File | Contents |
|------|----------|
| `public_stocks.json` | All stocks, ETFs, REITs, precious metals positions |
| `private_equity.json` | PE investments with value_history, IRR, probability |
| `funds.json` | Fund commitments, capital call schedules, value_history |
| `real_estate.json` | RE properties with value_history, mortgage data |
| `business.json` | Business investments with income_history |
| `debt.json` | Loans and debt obligations |
| `cashflow.json` | Income/expense data + actual cash + asset_sale_breakdown |
| `assumptions.json` | Scenario return rates per asset class + liquid return base rates |
| `asset_value_history.json` | Year-end totals per liquid asset class (Equity, ETF, REITs, Metals) |
| `ibkr_capital_flows.json` | IBKR-sourced net capital per asset class per year |
| `investment_plan.json` | Target allocation + planned annual investments |
| `fx_rates.json` | FX rates (EUR/X) |
| `dividend_config.json` | Dividend yields + actual dividend history |
| `overview_settings.json` | Ideal allocation percentages |
| `asset_history.json` | Historical asset values per year (manual entry) |
| `rules_notes.json` | User notes (this page) |
""")

with tab2:
    st.subheader("User Notes")
    st.caption("Add your own notes, rules, or reminders below. These are saved automatically.")

    notes_data = utils.load_json(utils.DATA_DIR / "rules_notes.json", {"notes": ""})
    current_notes = notes_data.get("notes", "")

    st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter your notes below</p>', unsafe_allow_html=True)
    edited_notes = st.text_area(
        "Notes (Markdown supported)",
        value=current_notes,
        height=400,
        key="rules_notes_editor"
    )

    if st.button("💾 Save Notes", type="primary"):
        utils.save_json(utils.DATA_DIR / "rules_notes.json", {"notes": edited_notes})
        st.success("Notes saved!")
        st.rerun()

    if current_notes:
        st.divider()
        st.markdown("### Preview")
        st.markdown(current_notes)
