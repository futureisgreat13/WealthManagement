import streamlit as st
import plotly.graph_objects as go
from utils import YEARS, ASSET_COLORS, get_scenario_values, fmt_eur_compact, fmt_eur

st.title("💶 Cash & Savings")
vals = get_scenario_values(st.session_state.get("scenario", "Base"))
data = vals["Cash"]

c1, c2 = st.columns(2)
c1.metric("Cash Position (2025)", fmt_eur_compact(data.get(2025, 0)))
c2.metric("Target 3% of portfolio", "€~500K–1.5M")

st.subheader("Cash Position Over Time")
colors = ["#EF4444" if data.get(y, 0) < 0 else ASSET_COLORS["Cash"] for y in YEARS]
fig = go.Figure(go.Bar(
    x=YEARS, y=[data.get(y, 0) for y in YEARS],
    marker_color=colors, marker_line_width=0,
    hovertemplate="Year %{x}: €%{y:,.0f}<extra></extra>"
))
fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)")
fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  height=300, margin=dict(l=0, r=0, t=10, b=30),
                  yaxis=dict(gridcolor="rgba(255,255,255,0.05)"))
st.plotly_chart(fig, width="stretch")

st.subheader("Cash Accounts")
accounts = [
    {"Account": "IB (Interactive Brokers)", "Amount": "€1,320,000", "Currency": "Multi"},
    {"Account": "ABN AMRO", "Amount": "€50,000", "Currency": "EUR"},
    {"Account": "Wise", "Amount": "€430,000", "Currency": "Multi"},
]
import pandas as pd
st.dataframe(pd.DataFrame(accounts), width="stretch", hide_index=True)
st.warning("⚠️ 2025 projected cash is negative (€-443K) due to heavy PE commitments and life expenses. Need to plan liquidity carefully.")
