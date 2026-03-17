import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils import IB_POSITIONS, fmt_eur, fmt_eur_compact, to_eur

st.title("📊 Interactive Brokers Positions")

# Calculate totals
total_val = sum(to_eur(p["value"], p["currency"]) for p in IB_POSITIONS)
total_cost = sum(to_eur(p["cost"], p["currency"]) for p in IB_POSITIONS)
pnl = total_val - total_cost

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total IB Value (EUR)", fmt_eur_compact(total_val))
c2.metric("Total Cost Basis", fmt_eur_compact(total_cost))
c3.metric("Total P&L", fmt_eur_compact(pnl), f"{pnl/total_cost*100:+.1f}%" if total_cost else "")
c4.metric("# Positions", str(len(IB_POSITIONS)))

# By type breakdown
st.subheader("Breakdown by Type")
by_type = {}
for p in IB_POSITIONS:
    t = p["type"]
    by_type[t] = by_type.get(t, 0) + to_eur(p["value"], p["currency"])

type_colors = {"Equity": "#10B981", "ETF": "#6366F1", "REITs": "#F59E0B", "Precious Metals": "#EAB308"}
fig_pie = go.Figure(go.Pie(
    labels=list(by_type.keys()), values=list(by_type.values()),
    hole=0.5, marker=dict(colors=[type_colors.get(t, "#94A3B8") for t in by_type.keys()]),
    textinfo="label+percent"
))
fig_pie.update_layout(
    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=350,
    margin=dict(l=0, r=0, t=10, b=10)
)
st.plotly_chart(fig_pie, width="stretch")

# Sort options
sort_col = st.selectbox("Sort by", ["Value (high to low)", "Return (high to low)", "Return (low to high)", "Symbol"])
if sort_col == "Value (high to low)":
    sorted_pos = sorted(IB_POSITIONS, key=lambda x: -to_eur(x["value"], x["currency"]))
elif sort_col == "Return (high to low)":
    sorted_pos = sorted(IB_POSITIONS, key=lambda x: -x["ret"])
elif sort_col == "Return (low to high)":
    sorted_pos = sorted(IB_POSITIONS, key=lambda x: x["ret"])
else:
    sorted_pos = sorted(IB_POSITIONS, key=lambda x: x["symbol"])

# Positions table
st.subheader("All Positions")
rows = []
for p in sorted_pos:
    val_eur = to_eur(p["value"], p["currency"])
    cost_eur = to_eur(p["cost"], p["currency"])
    rows.append({
        "Symbol": p["symbol"], "Type": p["type"], "Currency": p["currency"],
        "Qty": f'{p["qty"]:,}',
        "Market Value (EUR)": fmt_eur(val_eur),
        "Cost Basis (EUR)": fmt_eur(cost_eur),
        "P&L (EUR)": fmt_eur(val_eur - cost_eur),
        "Return %": f'{p["ret"]*100:+.1f}%'
    })
df = pd.DataFrame(rows)
st.dataframe(df, width="stretch", hide_index=True, height=700)

# Winners and losers
st.subheader("Top Performers & Biggest Losers")
col_win, col_lose = st.columns(2)
winners = sorted(IB_POSITIONS, key=lambda x: -x["ret"])[:5]
losers = sorted(IB_POSITIONS, key=lambda x: x["ret"])[:5]

with col_win:
    st.markdown("**🟢 Top Winners**")
    for p in winners:
        st.write(f"  **{p['symbol']}**: {p['ret']*100:+.1f}% ({fmt_eur_compact(to_eur(p['value'], p['currency']))})")

with col_lose:
    st.markdown("**🔴 Biggest Losers**")
    for p in losers:
        st.write(f"  **{p['symbol']}**: {p['ret']*100:+.1f}% ({fmt_eur_compact(to_eur(p['value'], p['currency']))})")

# By currency
st.subheader("Currency Exposure")
by_ccy = {}
for p in IB_POSITIONS:
    c = p["currency"]
    by_ccy[c] = by_ccy.get(c, 0) + p["value"]
for ccy, val in sorted(by_ccy.items(), key=lambda x: -x[1]):
    pct = val / sum(by_ccy.values()) * 100
    st.write(f"**{ccy}**: {fmt_eur_compact(val)} local — {pct:.1f}% of IB")
