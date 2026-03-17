import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils import (IB_POSITIONS, YEARS, ASSET_COLORS, get_scenario_values,
                   fmt_eur, fmt_eur_compact, DEFAULT_FX, to_eur)

st.title("📈 Equity")
scenario = st.session_state.get("scenario", "Base")
vals = get_scenario_values(scenario)
data = vals["Equity"]

# Filter IB positions
positions = [p for p in IB_POSITIONS if p["type"] in ("Equity", "ETF")]
total_val = sum(to_eur(p["value"], p["currency"]) for p in positions)
total_cost = sum(to_eur(p["cost"], p["currency"]) for p in positions)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio Value (2025)", fmt_eur_compact(data.get(2025, 0)))
c2.metric("IB Market Value", fmt_eur_compact(total_val))
c3.metric("IB Cost Basis", fmt_eur_compact(total_cost))
pnl = total_val - total_cost
c4.metric("Unrealized P&L", fmt_eur_compact(pnl), f"{pnl/total_cost*100:+.1f}%" if total_cost else "—")

# Value chart
st.subheader("Equity Value Projection")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=YEARS, y=[data.get(y, 0) for y in YEARS],
    fill="tozeroy", line=dict(color=ASSET_COLORS["Equity"], width=2),
    fillcolor=ASSET_COLORS["Equity"] + "33"
))
fig.add_vline(x=2025, line_dash="dash", line_color="rgba(255,255,255,0.2)")
fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  height=300, margin=dict(l=0, r=0, t=10, b=30),
                  yaxis=dict(gridcolor="rgba(255,255,255,0.05)"))
st.plotly_chart(fig, width="stretch")

# Positions table
st.subheader("IB Positions — Equity & ETFs")
rows = []
for p in sorted(positions, key=lambda x: -x["value"]):
    val_eur = to_eur(p["value"], p["currency"])
    cost_eur = to_eur(p["cost"], p["currency"])
    rows.append({
        "Symbol": p["symbol"], "Type": p["type"], "Currency": p["currency"],
        "Qty": f'{p["qty"]:,}', "Market Value (EUR)": fmt_eur(val_eur),
        "Cost Basis (EUR)": fmt_eur(cost_eur),
        "Return": f'{p["ret"]*100:+.1f}%'
    })
df = pd.DataFrame(rows)
st.dataframe(df, width="stretch", hide_index=True)

# By type breakdown
equity_only = [p for p in positions if p["type"] == "Equity"]
etf_only = [p for p in positions if p["type"] == "ETF"]
eq_val = sum(to_eur(p["value"], p["currency"]) for p in equity_only)
etf_val = sum(to_eur(p["value"], p["currency"]) for p in etf_only)

col1, col2 = st.columns(2)
col1.metric("Direct Equity", fmt_eur_compact(eq_val))
col2.metric("ETFs", fmt_eur_compact(etf_val))

st.caption("Key holdings: TSLA, META, SQ, OXY, TTE, PRX, SHEL. ETFs: SMH (semis), IEMG, ASHS, FXI, KBA (China/EM), VWO, CQQQ, KWEB.")
