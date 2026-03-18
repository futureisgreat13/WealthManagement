# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal wealth management dashboard built with Streamlit with the purpose to manage welth of an individual. Tracks and projects investment assets across different asset class with multi-scenario analysis, cash flow management, and investment planning. Uses a Bloomberg terminal-inspired dark theme. The idea is to make finance and investments simple for an individual.

## Development Commands

```bash
# Start dev server
streamlit run app.py
# Or via Claude Preview (configured in .claude/launch.json)
python3 -m streamlit run app.py --server.port 8501

# Install dependencies
pip install -r requirements.txt
```
Always start in Plan Mode. After plan approval, use ByPassPermission mode. In plan mode, ask all user permissions in 1 go to optimize the process, once user permission given, use it for the full session.

There is no test suite, linter, or build step. Verification is done manually through the Streamlit UI.

## Architecture

**Entry point:** `app.py` — sets up Streamlit multi-page navigation with three sections: Liquid Assets, Illiquid Assets, and Planning.

**Core module:** `utils.py` (~2,900 lines) — contains all shared logic: data I/O, formatting, asset total calculations, projection engines, income calculations, exit/investment schedules, IBKR import parsing, and the Bloomberg CSS theme. Every page imports from here.

**Pages:** `pages/` — each page is a standalone Streamlit script handling one asset class or feature. Pages use `utils.py` for data access and styling.

**Data store:** `data/*.json` — all persistence is flat JSON files, no database. Read/write via `load_json(path)` / `save_json(path, data)`.

## Key Constants (utils.py)

- `ASSET_CLASSES`: Equity, REITs, Real Estate, Private Equity, Funds, Business, Bonds, Precious Metals, Cash, Debt
- `LIQUID`: {Equity, REITs, Bonds, Precious Metals, Cash}
- `ILLIQUID`: {Private Equity, Real Estate, Funds, Business, Debt}
- `SCENARIOS`: Super Bear, Bear, Base, Bull
- `CURRENCIES`: EUR, USD, GBP, INR, HKD, JPY, CAD, AUD, CHF
- `CURRENT_YEAR`: dynamically set to current year
- `BASE_YEAR`: CURRENT_YEAR - 2 (last confirmed year-end data)
- All values normalized to EUR internally

## Key Patterns

- **Formatting:** Use `fmt_eur()`, `fmt_eur_short()`, `fmt_pct()` for display values. Use `color_negative()` to red-style negative numbers.
- **Styling:** Call `inject_bloomberg_css()` for the dark theme. Use `bloomberg_chart_layout()` for Plotly chart config.
- **Tables (read-only):** `render_aggrid_table()` for display-only grids with filtering via st-aggrid.
- **Tables (editable):** `render_editable_aggrid_table()` for editable grids with per-cell coloring and formula support. Use this instead of `st.data_editor()` for valuation tables. Never create redundant read-only + editable tables — always use a single editable table. Use `st.data_editor()` only when `num_rows="dynamic"` is needed (adding/deleting rows).
- **Cell coloring:** Apply per-CELL, not per-ROW. Use `build_valuation_style_maps(col_source_map)` to generate bg_style_map and cell_style_map. Colors: yellow bg (`BG_INPUT`) = user input, blue bg (`BG_IBKR`) = IBKR import, default = calculated/formula.
- **Formulas:** Never use `inject_formulas_for_edit()` with `st.data_editor()` NumberColumns (causes type error). For AgGrid, use `editor_key` param + `get_formula_map()` for tooltips. `process_math_in_df()` evaluates formulas on save.
- **Page layout:** No redundant tabs. Use sections with `st.subheader()` + `st.divider()` instead of `st.tabs()` for illiquid asset pages. Liquid asset pages keep Positions/Valuations/Edit tabs since they serve distinct purposes.
- **Session state:** `st.session_state.scenario` controls active scenario (default "Base").
- **Asset totals:** Each asset class has a `get_[asset]_total_eur(fx_rates)` function. `get_all_totals_eur(fx_rates)` returns a dict of all. `get_net_worth_eur(fx_rates)` for total portfolio.
- **Projections:** `get_portfolio_projection_v2(scenario, fx_rates, assumptions, years)` for forward projections. Return assumptions and scenario multipliers live in `data/assumptions.json`.
- **FX:** Rates stored in `data/fx_rates.json`, loaded via `load_fx_rates()`. All cross-currency positions convert to EUR.
- **Data source coloring:** Data is either calculated from formulas or input from user or IBKR. Formula/calculated cells = white text (default). User-input cells = yellow background. IBKR-imported cells = blue background. This applies per-cell, not per-row. Helps users distinguish hardcoded/input numbers from calculated numbers.
- **Visualisation:** Maximize data/space ratio — merge tables, delete redundant views when possible. One editable table instead of a display table + edit table.
- **Maths:** Any editable cell must allow math expressions like =500*2/EURUSD. Use `process_math_in_df()` to evaluate.
- **Formatting:** Numbers displayed in K & M with 0 decimal places for K and 1 decimal place for M. Example: 100000 → 100K, 1000000 → 1.0M. Use `_eur_formatter_js()` for AgGrid, `fmt_eur_short()` for display.
- **Missing data indicators:** On asset class pages, check if base year (CURRENT_YEAR - 1) data is complete. Show red warning above tables for missing items: valuations, capital call actuals, and distribution data. Format: `"⚠️ X items missing {base_year} year-end data: [names]"`. Include a "Last Updated" column showing the most recent year with user-entered data.
- **Unsaved changes warning:** Use `track_unsaved_changes(key, orig_df, edited_df)` after each editor render, `show_unsaved_warning()` at top of page, and `clear_unsaved(key)` after successful save. This is app-wide — works across tabs and pages.
- **Delete confirmation:** When saving editable tables with `num_rows="dynamic"`, use `check_deleted_items(original_items, edited_df, name_col)` to detect removed rows, then `handle_save_with_delete_confirmation(key, deleted_names)` to show a confirmation warning before actually deleting. Only save when result is `"save"`. Pattern: `deleted = utils.check_deleted_items(items, edited, "name"); result = utils.handle_save_with_delete_confirmation("key", deleted); if result == "save": ...save...; elif result == "cancelled": st.rerun()`.
- Always fact check when implementing something.
- Ask user questions in the middle of execution if stuck.

