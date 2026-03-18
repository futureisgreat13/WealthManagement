import streamlit as st
import pandas as pd
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("⚙️ FX Rates & Assumptions")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)

# --- FX Rates ---
st.subheader("FX Rates (EUR/X)")
_last_fx = st.session_state.get("_fx_last_refresh")
if _last_fx:
    st.caption(f"Auto-updated: {_last_fx.strftime('%Y-%m-%d %H:%M')}")
fx = utils.load_fx_rates()
pairs = ["EURUSD", "EURINR", "EURGBP", "EURHKD", "EURJPY", "EURCAD", "EURAUD", "EURCHF"]

cols = st.columns(4)
new_fx = {}
for i, pair in enumerate(pairs):
    with cols[i % 4]:
        # Only pass value if widget key not already in session state (avoids Streamlit warning)
        kwargs = {"label": pair, "step": 0.001, "format": "%.4f", "key": f"fx_{pair}"}
        if f"fx_{pair}" not in st.session_state:
            kwargs["value"] = float(fx.get(pair, 1.0))
        new_fx[pair] = st.number_input(**kwargs)

if st.button("💾 Save FX Rates", type="primary"):
    utils.save_fx_rates(new_fx)
    st.session_state.pop("_fx_live_rates", None)
    st.success("FX rates saved!")

st.divider()

# --- Liquid Asset Scenario Returns ---
st.subheader("Liquid Asset Scenario Returns (%/year)")
st.caption("Flat return rates per scenario for liquid assets. Used directly in projections.")
assumptions = utils.load_assumptions()

LIQUID_SCENARIO_ACS = ["Equity", "REITs", "Precious Metals", "Cash"]
liquid_rows = []
for ac in LIQUID_SCENARIO_ACS:
    a = assumptions.get(ac, {})
    if not isinstance(a, dict):
        a = {}
    liquid_rows.append({
        "Asset Class": ac,
        "Super Bear %": a.get("super_bear", 0),
        "Bear %": a.get("bear", 0),
        "Base %": a.get("base", 0),
        "Bull %": a.get("bull", 0),
    })

liquid_df = pd.DataFrame(liquid_rows)
liquid_numeric = ["Super Bear %", "Bear %", "Base %", "Bull %"]
for col in liquid_numeric:
    if col in liquid_df.columns:
        liquid_df[col] = liquid_df[col].astype(str)
st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter scenario return rates</p>', unsafe_allow_html=True)
edited_liquid = st.data_editor(liquid_df, use_container_width=True, hide_index=True, key="liquid_assumptions_editor",
    column_config={
        "Super Bear %": st.column_config.TextColumn("Super Bear %"),
        "Bear %": st.column_config.TextColumn("Bear %"),
        "Base %": st.column_config.TextColumn("Base %"),
        "Bull %": st.column_config.TextColumn("Bull %"),
    },
    disabled=["Asset Class"])
edited_liquid = utils.process_math_in_df(edited_liquid, ["Super Bear %", "Bear %", "Base %", "Bull %"], editor_key="fx_scenario_multipliers")

if st.button("💾 Save Liquid Returns", type="primary", key="save_liquid_scenario"):
    existing = utils.load_assumptions()
    for _, row in edited_liquid.iterrows():
        existing[row["Asset Class"]] = {
            "super_bear": float(row["Super Bear %"]),
            "bear": float(row["Bear %"]),
            "base": float(row["Base %"]),
            "bull": float(row["Bull %"]),
        }
    existing["Debt"] = {"super_bear": 0, "bear": 0, "base": 0, "bull": 0}
    utils.save_assumptions(existing)
    st.success("Liquid scenario returns saved!")

st.divider()

# --- IRR-Based Asset Scenario Settings (PE, RE, Funds, Business) ---
st.subheader("IRR-Based Asset Scenarios (PE, RE, Funds, Business)")
st.caption("These assets use per-item IRR × probability for projections. "
           "Multipliers scale the base IRR/probability per scenario. "
           "Optionally set a fixed return % to override the multiplier approach entirely.")

pe_mults = utils.get_all_scenario_multipliers("pe")
re_mults = utils.get_all_scenario_multipliers("re")

# Load any fixed overrides from assumptions
IRR_BASED_ACS = ["Private Equity", "Funds", "Real Estate", "Business"]

irr_rows = []
for s in utils.SCENARIOS:
    pe_m = pe_mults.get(s, {"irr": 1.0, "prob": 1.0})
    re_m = re_mults.get(s, {"irr": 1.0, "prob": 1.0})
    row = {
        "Scenario": s,
        "PE IRR ×": pe_m["irr"],
        "PE Prob ×": pe_m["prob"],
        "RE IRR ×": re_m["irr"],
        "RE Prob ×": re_m["prob"],
    }
    # Fixed % overrides — if set, these replace the multiplier approach for that scenario
    for ac in IRR_BASED_ACS:
        a = assumptions.get(ac, {})
        if isinstance(a, dict):
            key = utils.SCENARIO_KEYS.get(s, "base")
            val = a.get(key, None)
            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                row[f"{ac} Override %"] = val
            else:
                row[f"{ac} Override %"] = None
        else:
            row[f"{ac} Override %"] = None
    irr_rows.append(row)

irr_df = pd.DataFrame(irr_rows)
irr_numeric_cols = ["PE IRR ×", "PE Prob ×", "RE IRR ×", "RE Prob ×"] + [f"{ac} Override %" for ac in IRR_BASED_ACS]
for col in irr_numeric_cols:
    if col in irr_df.columns:
        irr_df[col] = irr_df[col].astype(str)
st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — multipliers + optional fixed % overrides (leave empty to use multipliers)</p>', unsafe_allow_html=True)
col_config = {
    "PE IRR ×": st.column_config.TextColumn("PE IRR ×"),
    "PE Prob ×": st.column_config.TextColumn("PE Prob ×"),
    "RE IRR ×": st.column_config.TextColumn("RE IRR ×"),
    "RE Prob ×": st.column_config.TextColumn("RE Prob ×"),
}
for ac in IRR_BASED_ACS:
    col_config[f"{ac} Override %"] = st.column_config.TextColumn(f"{ac} Override %")

edited_irr = st.data_editor(irr_df, use_container_width=True, hide_index=True,
    column_config=col_config,
    disabled=["Scenario"], key="irr_mult_editor")
edited_irr = utils.process_math_in_df(edited_irr, irr_numeric_cols, editor_key="fx_irr_overrides")

if st.button("💾 Save IRR Settings", type="primary", key="save_irr_settings"):
    new_pe = {}
    new_re = {}
    for _, row in edited_irr.iterrows():
        s = row["Scenario"]
        new_pe[s] = {"irr": float(row["PE IRR ×"]), "prob": float(row["PE Prob ×"])}
        new_re[s] = {"irr": float(row["RE IRR ×"]), "prob": float(row["RE Prob ×"])}

    existing = utils.load_assumptions()
    existing["pe_scenario_multipliers"] = new_pe
    existing["re_scenario_multipliers"] = new_re

    # Save fixed % overrides
    for ac in IRR_BASED_ACS:
        scenario_dict = {}
        for _, row in edited_irr.iterrows():
            s = row["Scenario"]
            key = utils.SCENARIO_KEYS.get(s, "base")
            val = row.get(f"{ac} Override %")
            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                scenario_dict[key] = float(val)
            else:
                scenario_dict[key] = float('nan')
        existing[ac] = scenario_dict

    utils.save_assumptions(existing)
    st.success("IRR settings saved!")

st.divider()

# --- Dividend Yield Settings ---
st.subheader("Expected Dividend Yields (%/year)")
st.caption("Used for projecting future dividend income in Cash Flow. "
           "Applied to the projected value of each asset class.")
div_config = utils.load_dividend_config()
dc1, dc2, dc3 = st.columns(3)
eq_yld = dc1.number_input("Equity Dividend Yield %", value=float(div_config.get("equity_yield_pct", 2.5)),
                            step=0.1, format="%.1f", key="eq_yield")
reit_yld = dc2.number_input("REIT Dividend Yield %", value=float(div_config.get("reit_yield_pct", 5.0)),
                              step=0.1, format="%.1f", key="reit_yield")
pe_yld = dc3.number_input("PE Dividend Yield %", value=float(div_config.get("pe_yield_pct", 3.0)),
                            step=0.1, format="%.1f", key="pe_yield")

if st.button("💾 Save Dividend Yields", type="primary", key="save_div_yields"):
    div_config["equity_yield_pct"] = eq_yld
    div_config["reit_yield_pct"] = reit_yld
    div_config["pe_yield_pct"] = pe_yld
    utils.save_json(utils.DATA_DIR / "dividend_config.json", div_config)
    st.success("Dividend yields saved!")

# --- Actual Dividend History ---
st.subheader("Actual Dividends Received")
st.caption("Enter actual dividends received per asset class per year. "
           "For future years without actuals, yield % above is applied to projected capital.")
actual_divs = div_config.get("actual_dividends", {})
div_classes = ["Equity", "REITs", "PE"]
div_years = list(range(2020, utils.CURRENT_YEAR + 2))

div_rows = []
for ac in div_classes:
    row = {"Asset Class": ac}
    for yr in div_years:
        row[str(yr)] = actual_divs.get(ac, {}).get(str(yr), 0)
    div_rows.append(row)

div_df = pd.DataFrame(div_rows)
div_numeric_cols = [str(yr) for yr in div_years]
for col in div_numeric_cols:
    if col in div_df.columns:
        div_df[col] = div_df[col].astype(str)
st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter your values below</p>', unsafe_allow_html=True)
st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
edited_divs = st.data_editor(div_df, use_container_width=True, hide_index=True,
    column_config={str(yr): st.column_config.TextColumn(str(yr)) for yr in div_years},
    disabled=["Asset Class"], key="div_history_editor")
edited_divs = utils.process_math_in_df(edited_divs, div_numeric_cols, editor_key="fx_dividends")

if st.button("💾 Save Dividend History", type="primary", key="save_div_history"):
    new_actual = {}
    for _, row in edited_divs.iterrows():
        ac = row["Asset Class"]
        vals = {}
        for yr in div_years:
            v = float(row.get(str(yr), 0) or 0)
            if v > 0:
                vals[str(yr)] = v
        new_actual[ac] = vals
    div_config["actual_dividends"] = new_actual
    utils.save_json(utils.DATA_DIR / "dividend_config.json", div_config)
    st.success("Dividend history saved!")

st.divider()

# --- Live Market Prices ---
st.subheader("Live Market Prices")
market = utils.get_live_market_data()
if market.get("last_updated"):
    st.caption(f"Auto-updated every 15 min. Last refresh: {market['last_updated']}")
if market.get("prices"):
    price_rows = []
    fx_rates = utils.load_fx_rates()
    for name, info in market["prices"].items():
        price_eur = utils.to_eur(info["price"], info["currency"], fx_rates)
        price_rows.append({
            "Asset": name,
            "Price": f'{info["price"]:,.2f}',
            "Currency": info["currency"],
            "Price (EUR)": utils.fmt_eur(price_eur),
        })
    if price_rows:
        utils.render_aggrid_table(pd.DataFrame(price_rows), key="aggrid_market_prices",
                                  height=min(400, len(price_rows) * 32 + 60))
else:
    st.info("Market prices unavailable. Check internet connection.")
