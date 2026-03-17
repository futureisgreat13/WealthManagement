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
- **Tables:** `render_aggrid_table()` for advanced grids with filtering/editing via st-aggrid.
- **Session state:** `st.session_state.scenario` controls active scenario (default "Base").
- **Asset totals:** Each asset class has a `get_[asset]_total_eur(fx_rates)` function. `get_all_totals_eur(fx_rates)` returns a dict of all. `get_net_worth_eur(fx_rates)` for total portfolio.
- **Projections:** `get_portfolio_projection_v2(scenario, fx_rates, assumptions, years)` for forward projections. Return assumptions and scenario multipliers live in `data/assumptions.json`.
- **FX:** Rates stored in `data/fx_rates.json`, loaded via `load_fx_rates()`. All cross-currency positions convert to EUR.
- ** Data is either calculated from some raw data with formulas or input from user or IBKR. if the data is a formula/ logic then show text in white, if a user is responsible to input that data or has dont it historically then keep the background of that cell yellow, if the data is coming from IBKR import then keep the background of that cell blue. Follow this for every single page. Idea is not to have random numbers and let the user know if the number is hardcoded/ or an inputted number vs calculated number.
 - Visualisation - you want to maximize data/space ratio so try to merge tables or delete things when possible. Tables need to be editable instead of a second table to edit numbers in the main table.
 - Maths - any cell where its editable needs to allow maths functions like =500*2/EURUSD.
 - Always fact check when implementing something
- Ask user questions in the middle of execution if you get stuck aywhere
-Formaating - Numbers need to be in k & m with 0 decimal places for k and 1 decimal place for m. For example 100000 needs to be shown as 100k, 1000000 needs to be shown as 1m.
 - 

