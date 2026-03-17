import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils
from utils import (DEFAULT_FX, SCENARIO_MULTIPLIERS, SCENARIOS, ASSET_CLASSES,
                   ASSET_COLORS, fmt_pct)

st.title("⚙️ FX Rates & Settings")

st.subheader("Current Scenario")
st.info(f"Active scenario: **{st.session_state.get('scenario', 'Base')}** — change from the top bar on any page.")

# FX Rates
st.subheader("FX Rates (EUR base)")
st.caption("All investments are converted to EUR using these rates.")
cols = st.columns(4)
for i, (pair, rate) in enumerate(DEFAULT_FX.items()):
    cols[i % 4].metric(pair, f"{rate:.4f}")

st.divider()

# Scenario multipliers table
st.subheader("Scenario Multipliers")
st.caption("These multipliers are applied to projected values (2026+) for each asset class.")
rows = []
for asset in ASSET_CLASSES:
    row = {"Asset": asset}
    for sc in SCENARIOS:
        mult = SCENARIO_MULTIPLIERS[sc].get(asset, 1.0)
        row[sc] = f"{mult:.2f}x"
    rows.append(row)
df = pd.DataFrame(rows)
utils.render_aggrid_table(df, key="aggrid_settings_scenarios", height=400)

st.divider()

st.subheader("Target Allocation")
from utils import IDEAL_ALLOCATION
rows = []
for asset, target in IDEAL_ALLOCATION.items():
    rows.append({"Asset": asset, "Target %": f"{target*100:.1f}%", "Type": "Liquid" if asset in {"Equity", "REITs", "Bonds", "Precious Metals", "Cash"} else "Illiquid"})
utils.render_aggrid_table(pd.DataFrame(rows), key="aggrid_settings_allocation", height=400)

st.divider()
st.subheader("Data Notes")
st.write("""
- All values in EUR (end-of-year snapshots from Excel)
- Historical data (2020–2025): actual values from Master tab
- Projected data (2026–2033): base projections from Excel, adjusted by scenario multipliers
- IB positions: snapshot from IB data tab in Excel
- Cash flow: from Master 2 tab
- To update: replace data in `utils.py` or connect live data sources
""")

st.subheader("To-Do (from Excel)")
todos = [
    "Fund tax structure to share with Freek",
    "Funds distribution and year-end process",
    "Implement capital gain tax 2030+, remove wealth tax",
    "Year-end tax valuation process",
    "Add scenarios for depression (-50%) and hyperinflation (+100%)",
    "Pop up loan in 2026 before Optiver contract ends",
    "Plan for cash for AI bubble bust",
    "Invest more in China / Gold / Argentina?",
    "Get IB data for actual per-stock investment tracking",
    "Update Generic & fund year end valuations",
]
for t in todos:
    st.checkbox(t, key=f"todo_{t}")
