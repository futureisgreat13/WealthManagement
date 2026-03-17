import streamlit as st
import plotly.graph_objects as go
from utils import YEARS, ASSET_COLORS, get_scenario_values, fmt_eur_compact

st.title("🪙 Crypto")
vals = get_scenario_values(st.session_state.get("scenario", "Base"))
data = vals["Crypto"]

c1, c2 = st.columns(2)
c1.metric("Crypto (2025)", fmt_eur_compact(data.get(2025, 0)))
c2.metric("Target Allocation", "0.5%")

st.subheader("Crypto Value Over Time")
fig = go.Figure(go.Bar(
    x=YEARS, y=[data.get(y, 0) for y in YEARS],
    marker_color=ASSET_COLORS["Crypto"], marker_line_width=0
))
fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  height=300, margin=dict(l=0, r=0, t=10, b=30),
                  yaxis=dict(gridcolor="rgba(255,255,255,0.05)"))
st.plotly_chart(fig, width="stretch")

st.info("Crypto peaked at €800K in 2021, currently held at €100K. Small allocation maintained. From Master todo: 'Time to buy Bitcoin?'")
