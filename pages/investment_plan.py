import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("📊 Investment Plan")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)

fx = utils.load_fx_rates()
assumptions = utils.load_assumptions()
plan = utils.load_json(utils.DATA_DIR / "investment_plan.json", {})
target_alloc = plan.get("target_allocation", {})
planned_inv = plan.get("planned_investment_yr", {})
planned_by_year = plan.get("planned_investment_by_year", {})
dividend_yields = plan.get("dividend_yield_pct", {})

scenario = st.session_state.get("scenario", "Base")

# --- Use 2025 YE values (consistent with overview + tab headlines) ---
hist_by_asset = utils.get_historical_totals_by_asset(fx)
proj_data = utils.get_portfolio_projection_v2(scenario, fx, assumptions, years=16)
last_ye_yr = str(utils.CURRENT_YEAR - 1)  # "2025"
ye_values = hist_by_asset.get(last_ye_yr, {})

# Fallback: if an asset class has no YE value, use projection for that year
for ac in utils.ASSET_CLASSES:
    if ac not in ye_values or ye_values[ac] <= 0:
        if utils.CURRENT_YEAR - 1 in proj_data["years"]:
            idx = proj_data["years"].index(utils.CURRENT_YEAR - 1)
            ac_proj = proj_data["by_asset"].get(ac, [])
            ye_values[ac] = ac_proj[idx] if idx < len(ac_proj) else 0

total_positive = sum(max(0, v) for v in ye_values.values())

# --- Available Capital ---
available = utils.get_available_to_invest(fx)
liquid_total = sum(ye_values.get(ac, 0) for ac in utils.ASSET_CLASSES if ac in utils.LIQUID)
illiquid_total = sum(ye_values.get(ac, 0) for ac in utils.ASSET_CLASSES if ac in utils.ILLIQUID)

c1, c2, c3 = st.columns(3)
c1.metric("Available to Invest", utils.fmt_eur(available),
          help="From Cash Flow: income minus non-investment expenses")
c2.metric("Total Liquid", utils.fmt_eur(liquid_total))
c3.metric("Total Illiquid", utils.fmt_eur(illiquid_total))

st.divider()

# ==========================================================================
# TAB 1: Allocation & Settings   |   TAB 2: Projection & Dividends
# ==========================================================================
tab1, tab2 = st.tabs(["Allocation & Settings", "Projection & Dividends"])

# ---------- TAB 1: Allocation, Target %, Yield, Default Invest/yr ----------
with tab1:
    st.subheader("Allocation & Investment Settings")
    st.caption(f"Values as of {last_ye_yr} year-end. Target % is the single source of truth used by Overview.")

    rows = []
    for ac in utils.ASSET_CLASSES:
        val = ye_values.get(ac, 0)
        pct = (val / total_positive * 100) if total_positive > 0 else 0
        tgt = target_alloc.get(ac, 0)
        gap = pct - tgt
        yld = dividend_yields.get(ac, 0)
        div_income = val * yld / 100 if val > 0 else 0
        inv_yr = planned_inv.get(ac, 0)
        liq = "Liquid" if ac in utils.LIQUID else "Illiquid"

        rows.append({
            "Asset Class": ac,
            "Liquidity": liq,
            f"Value ({last_ye_yr})": utils.fmt_eur_short(val),
            "Current %": round(pct, 1),
            "Target %": tgt,
            "Diff %": round(gap, 1),
            "Div Yield %": yld,
            "Est. Dividends": utils.fmt_eur_short(div_income),
            "Default Invest/yr": inv_yr,
        })

    plan_df = pd.DataFrame(rows)

    # Total row
    total_val = sum(ye_values.get(ac, 0) for ac in utils.ASSET_CLASSES)
    total_div = sum(ye_values.get(ac, 0) * dividend_yields.get(ac, 0) / 100 for ac in utils.ASSET_CLASSES)
    total_inv = sum(planned_inv.get(ac, 0) for ac in utils.ASSET_CLASSES)
    total_tgt = sum(target_alloc.get(ac, 0) for ac in utils.ASSET_CLASSES)
    total_row_data = {
        "Asset Class": "TOTAL",
        "Liquidity": "",
        f"Value ({last_ye_yr})": utils.fmt_eur_short(total_val),
        "Current %": 100.0,
        "Target %": total_tgt,
        "Diff %": 0.0,
        "Div Yield %": 0.0,
        "Est. Dividends": utils.fmt_eur_short(total_div),
        "Default Invest/yr": total_inv,
    }
    plan_df = pd.concat([plan_df, pd.DataFrame([total_row_data])], ignore_index=True)

    st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable: Target %, Div Yield %, Default Invest/yr</p>', unsafe_allow_html=True)
    st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
    edited_plan = st.data_editor(
        plan_df, use_container_width=True, hide_index=True,
        column_config={
            "Target %": st.column_config.TextColumn("Target %"),
            "Div Yield %": st.column_config.TextColumn("Div Yield %"),
            "Default Invest/yr": st.column_config.TextColumn("Default Invest/yr"),
        },
        disabled=["Asset Class", "Liquidity", f"Value ({last_ye_yr})", "Current %",
                  "Diff %", "Est. Dividends"],
    )
    edited_plan = utils.process_math_in_df(edited_plan, ["Target %", "Div Yield %", "Default Invest/yr"], editor_key="investment_plan_targets")

    if st.button("💾 Save Settings", type="primary", key="save_settings"):
        new_target = {}
        new_invest = {}
        new_yields = {}
        for _, row in edited_plan.iterrows():
            ac = row["Asset Class"]
            if ac == "TOTAL":
                continue
            new_target[ac] = float(row.get("Target %", 0) or 0)
            new_invest[ac] = float(row.get("Default Invest/yr", 0) or 0)
            new_yields[ac] = float(row.get("Div Yield %", 0) or 0)
        plan["target_allocation"] = new_target
        plan["planned_investment_yr"] = new_invest
        plan["dividend_yield_pct"] = new_yields
        utils.save_json(utils.DATA_DIR / "investment_plan.json", plan)
        st.success("Settings saved!")
        st.rerun()

    # --- Suggested Capital Distribution ---
    st.subheader("Suggested Capital Distribution")
    st.caption("Based on allocation gap — where target % exceeds current %, proportional allocation of available capital.")

    positive_gaps = {}
    for ac in utils.ASSET_CLASSES:
        val = ye_values.get(ac, 0)
        pct = (val / total_positive * 100) if total_positive > 0 else 0
        tgt = target_alloc.get(ac, 0)
        gap = tgt - pct
        if gap > 0:
            positive_gaps[ac] = gap
    total_gap = sum(positive_gaps.values())

    if total_gap > 0 and available > 0:
        suggestions = {ac: available * (gap / total_gap) for ac, gap in positive_gaps.items()}
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=list(suggestions.keys()),
            x=list(suggestions.values()),
            orientation="h",
            marker_color=["#2563eb", "#10b981", "#8b5cf6", "#f59e0b", "#eab308",
                          "#ec4899", "#f97316", "#6366f1", "#14b8a6", "#a855f7"][:len(suggestions)],
            text=[utils.fmt_eur(v) for v in suggestions.values()],
            textposition="auto",
        ))
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
            xaxis_title="Suggested Allocation (EUR)", yaxis_title="",
            xaxis=dict(tickformat=",.0f"),
            height=max(200, len(suggestions) * 60 + 100),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No allocation gaps or no available capital to distribute.")

# ---------- TAB 2: Projection & Dividends ----------
with tab2:
    st.subheader("Portfolio Projection")
    st.caption("Based on Default Invest/yr from Settings tab. "
               "Per-year overrides can be set in each asset's Valuation tab.")

    years_list = list(range(utils.CURRENT_YEAR, utils.CURRENT_YEAR + 11))
    fig2 = go.Figure()

    colors = {"Equity": "#2563eb", "REITs": "#10b981", "Bonds": "#8b5cf6",
              "Precious Metals": "#f59e0b", "Cash": "#eab308", "Real Estate": "#ec4899",
              "Private Equity": "#ef4444", "Funds": "#f97316", "Business": "#6366f1",
              "Debt": "#a855f7"}

    total_proj = [0.0] * len(years_list)
    for ac in utils.ASSET_CLASSES:
        current_val = ye_values.get(ac, 0)
        ret = utils.get_return_pct(ac, scenario, assumptions)
        # Build per-year contributions
        ac_vals = [current_val]
        for yr in years_list[1:]:
            inv = utils.get_planned_investment(ac, yr)
            prev = ac_vals[-1]
            ac_vals.append(prev * (1 + ret / 100) + inv)
        for i in range(len(years_list)):
            total_proj[i] += ac_vals[i]
        if abs(current_val) > 1000:  # Only chart meaningful asset classes
            fig2.add_trace(go.Scatter(
                x=years_list, y=ac_vals, name=ac, mode="lines",
                line=dict(color=colors.get(ac, "#ffffff"), width=1.5, dash="dot"),
            ))

    fig2.add_trace(go.Scatter(
        x=years_list, y=total_proj, name="Total Portfolio", mode="lines+markers",
        line=dict(color="#4c8bf5", width=3), marker=dict(size=6),
    ))

    fig2.update_layout(
        template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
        xaxis_title="Year", yaxis_title="Value (EUR)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(tickformat=",.0f"), hovermode="x unified",
    )
    st.plotly_chart(fig2, use_container_width=True)

    # --- Dividend Income Projection ---
    st.subheader("Projected Dividend Income")
    st.caption("Annual dividend income based on projected values × dividend yield %.")

    plan_year_strs = [str(yr) for yr in years_list]
    div_proj_rows = []
    for ac in utils.ASSET_CLASSES:
        yld = dividend_yields.get(ac, 0)
        if yld <= 0:
            continue
        current_val = ye_values.get(ac, 0)
        ret = utils.get_return_pct(ac, scenario, assumptions)
        row = {"Asset Class": ac, "Yield %": yld}
        val = current_val
        for yr in years_list:
            inv = utils.get_planned_investment(ac, yr)
            val = val * (1 + ret / 100) + inv
            row[str(yr)] = round(val * yld / 100)
        div_proj_rows.append(row)

    if div_proj_rows:
        # Total row
        total_div_row = {"Asset Class": "TOTAL", "Yield %": 0}
        for yr_str in plan_year_strs:
            total_div_row[yr_str] = sum(r.get(yr_str, 0) for r in div_proj_rows)
        div_proj_rows.append(total_div_row)
        div_df = pd.DataFrame(div_proj_rows)
        div_col_config = {yr_str: st.column_config.TextColumn() for yr_str in plan_year_strs}
        div_col_config["Yield %"] = st.column_config.TextColumn()
        utils.render_aggrid_table(div_df, key="aggrid_div_projection",
                                  height=min(350, max(200, len(div_proj_rows) * 32 + 40)),
                                  numeric_cols=plan_year_strs,
                                  highlight_total_row=True)
