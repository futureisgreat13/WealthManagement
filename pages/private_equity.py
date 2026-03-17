import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("💼 Private Equity")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)

items = utils.load_json(utils.DATA_DIR / "private_equity.json", [])

active = [i for i in items if i.get("status") == "Active" and i.get("type") != "Real Estate"]
exited = [i for i in items if i.get("status") == "Exited"]
written_off = [i for i in items if i.get("status") == "Written Off"]

total_invested = sum(i.get("amount_invested_eur", 0) for i in items)

# Active Value: use compute_pe_timeline for latest completed year (same as Overview)
latest_yr_int = utils.CURRENT_YEAR - 1  # Last completed year
pe_val_latest = utils.compute_pe_timeline([latest_yr_int], "Base")
total_current = pe_val_latest[0] if pe_val_latest else 0
year_label = f" ({latest_yr_int} YE)"

# Check if any items are missing year-end values for latest year
val_items = utils._get_pe_valuation_items()
missing_items = []
for p in val_items:
    status = p.get("status", "Active")
    exit_yr = p.get("expected_exit_year", 9999)
    yr_invested = p.get("year_invested", 9999)
    if latest_yr_int < yr_invested:
        continue
    if status == "Exited" and latest_yr_int >= exit_yr:
        continue
    vh = p.get("value_history", {})
    if str(latest_yr_int) not in vh:
        missing_items.append(p.get("name", "Unknown"))
missing_note = ""
if missing_items:
    missing_note = f' <span style="color:red">* {len(missing_items)} items without {latest_yr_int} valuation</span>'

total_exit_proceeds = sum(i.get("exit_value_eur", i.get("current_value_eur", 0)) for i in exited)
total_dividends = sum(i.get("annual_dividend_eur", 0) for i in active)
total_moic = (total_current + total_exit_proceeds) / total_invested if total_invested > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"Portfolio Value{year_label}", utils.fmt_eur(total_current))
c2.metric("Total Invested", utils.fmt_eur(total_invested))
c3.metric("Exit Proceeds", utils.fmt_eur(total_exit_proceeds))
c4.metric("Annual Dividends", utils.fmt_eur(total_dividends))
c5.metric("MOIC", f"{total_moic:.2f}x")
if missing_note:
    st.markdown(missing_note, unsafe_allow_html=True)

st.divider()

# --- Tabs: Positions + Valuations only ---
tab1, tab2 = st.tabs(["Positions", "Valuations"])

with tab1:
    # --- Active Positions (editable) ---
    if active or True:  # Always show editor
        st.subheader(f"Active ({len(active)})")
        edit_rows = [{
            "name": p.get("name", ""),
            "year_invested": p.get("year_invested", 2020),
            "type": p.get("type", "Private Equity"),
            "amount_invested_eur": p.get("amount_invested_eur", 0),
            "current_value_eur": p.get("current_value_eur", 0),
            "exit_value_eur": p.get("exit_value_eur", 0),
            "annual_dividend_eur": p.get("annual_dividend_eur", 0),
            "expected_irr_pct": p.get("expected_irr_pct", 0),
            "success_probability_pct": p.get("success_probability_pct", 80),
            "expected_exit_year": p.get("expected_exit_year", 2028),
            "status": p.get("status", "Active"),
            "notes": p.get("notes", ""),
        } for p in items]

        edit_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(
            columns=["name", "year_invested", "type", "amount_invested_eur",
                     "current_value_eur", "exit_value_eur", "annual_dividend_eur",
                     "expected_irr_pct", "success_probability_pct",
                     "expected_exit_year", "status", "notes"])

        row_height = min(500, max(250, len(edit_rows) * 32 + 40))
        st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — add/edit positions directly. Add rows at the bottom.</p>', unsafe_allow_html=True)
        st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
        edited = st.data_editor(edit_df, use_container_width=True, hide_index=True, num_rows="dynamic",
            height=row_height,
            column_config={
                "status": st.column_config.SelectboxColumn("Status", options=["Active", "Exited", "Written Off"]),
                "type": st.column_config.SelectboxColumn("Type", options=["Private Equity", "Venture Capital", "Fund", "Other"]),
                "amount_invested_eur": st.column_config.NumberColumn("Invested (EUR)", format="€%.0f"),
                "current_value_eur": st.column_config.NumberColumn("Current Value", format="€%.0f"),
                "exit_value_eur": st.column_config.NumberColumn("Exit Value", format="€%.0f"),
                "annual_dividend_eur": st.column_config.NumberColumn("Dividend/yr", format="€%.0f"),
                "expected_irr_pct": st.column_config.NumberColumn("IRR %", format="%.1f%%"),
                "success_probability_pct": st.column_config.NumberColumn("Prob %", format="%.0f%%"),
            })
        edited = utils.process_math_in_df(edited, ["amount_invested_eur", "current_value_eur", "exit_value_eur", "annual_dividend_eur", "expected_irr_pct", "success_probability_pct"])

        if st.button("💾 Save Positions", type="primary", key="pe_save"):
            new_items = []
            for j, (_, row) in enumerate(edited.iterrows()):
                if row.get("name"):
                    orig = items[j] if j < len(items) else {}
                    new_items.append({
                        "id": orig.get("id", utils.new_id()),
                        "name": row["name"],
                        "year_invested": int(row.get("year_invested", 2020) or 2020),
                        "type": row.get("type", "Private Equity"),
                        "amount_invested_eur": float(row.get("amount_invested_eur", 0) or 0),
                        "current_value_eur": float(row.get("current_value_eur", 0) or 0),
                        "exit_value_eur": float(row.get("exit_value_eur", 0) or 0),
                        "annual_dividend_eur": float(row.get("annual_dividend_eur", 0) or 0),
                        "expected_irr_pct": float(row.get("expected_irr_pct", 0) or 0),
                        "success_probability_pct": float(row.get("success_probability_pct", 80) or 80),
                        "expected_exit_year": int(row.get("expected_exit_year", 2028) or 2028),
                        "status": row.get("status", "Active"),
                        "notes": row.get("notes", ""),
                        "value_history": orig.get("value_history", {}),
                    })
            utils.save_json(utils.DATA_DIR / "private_equity.json", new_items)
            st.success("Saved!")
            st.rerun()

    # --- Exited Positions ---
    if exited:
        st.subheader(f"Exited ({len(exited)})")
        exit_rows = []
        for p in exited:
            exit_val = p.get("exit_value_eur", p.get("current_value_eur", 0))
            invested = p.get("amount_invested_eur", 0)
            pnl = exit_val - invested
            exit_rows.append({
                "Name": p.get("name", ""),
                "Year In": p.get("year_invested", ""),
                "Year Out": p.get("expected_exit_year", ""),
                "Invested": utils.fmt_eur_short(invested),
                "Exit Value": utils.fmt_eur_short(exit_val),
                "P&L": utils.fmt_eur_short(pnl),
                "MOIC": f"{exit_val / invested:.2f}x" if invested > 0 else "0x",
                "Notes": p.get("notes", ""),
            })
        df_exited = pd.DataFrame(exit_rows)
        row_height = min(400, max(200, len(exit_rows) * 32 + 40))
        utils.render_aggrid_table(df_exited, key="aggrid_pe_exited", height=row_height)

    # --- Written Off ---
    if written_off:
        st.subheader(f"Written Off ({len(written_off)})")
        wo_rows = []
        for p in written_off:
            wo_rows.append({
                "Name": p.get("name", ""),
                "Year": p.get("year_invested", ""),
                "Lost": utils.fmt_eur_short(p.get("amount_invested_eur", 0)),
                "Notes": p.get("notes", ""),
            })
        df_wo = pd.DataFrame(wo_rows)
        utils.render_aggrid_table(df_wo, key="aggrid_pe_writtenoff", height=300)

    # --- Portfolio Value Over Time Chart (moved from Value History) ---
    st.subheader("Portfolio Value Over Time")
    all_years_chart = set()
    for p in items:
        vh = p.get("value_history", {})
        if vh:
            all_years_chart.update(int(y) for y in vh.keys())
        yr = p.get("year_invested", utils.CURRENT_YEAR)
        all_years_chart.add(yr)
    all_years_chart.add(utils.CURRENT_YEAR)
    sorted_years_chart = sorted(all_years_chart)

    year_totals = {y: 0 for y in sorted_years_chart}
    for p in items:
        vh = p.get("value_history", {})
        for y in sorted_years_chart:
            val = vh.get(str(y), 0)
            if not vh and p.get("status") == "Active":
                if y >= p.get("year_invested", 9999):
                    val = p.get("current_value_eur", 0)
            year_totals[y] += val

    if any(v > 0 for v in year_totals.values()):
        fig_total = go.Figure()
        fig_total.add_trace(go.Scatter(
            x=sorted_years_chart,
            y=[year_totals[y] for y in sorted_years_chart],
            mode="lines+markers",
            line=dict(color="#4c8bf5", width=3),
            marker=dict(size=6),
            name="Total PE Value",
            text=[utils.fmt_eur(year_totals[y]) for y in sorted_years_chart],
            hovertemplate="%{x}: %{text}",
        ))
        fig_total.update_layout(
            template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
            xaxis_title="Year", yaxis_title="Value (EUR)",
            yaxis=dict(tickformat=",.0f"), hovermode="x unified",
        )
        st.plotly_chart(fig_total, use_container_width=True)

    # --- Exits by Year Chart ---
    st.subheader("Exits by Year")
    exit_data = {}
    for p in active:
        exit_yr = p.get("expected_exit_year", 3000)
        if exit_yr > 2050:
            continue
        expected_val = p.get("current_value_eur", 0) * (p.get("success_probability_pct", 0) / 100)
        exit_data[exit_yr] = exit_data.get(exit_yr, 0) + expected_val
    for p in exited:
        exit_yr = p.get("expected_exit_year", 3000)
        if exit_yr > 2050:
            continue
        exit_val = p.get("exit_value_eur", 0)
        exit_data[exit_yr] = exit_data.get(exit_yr, 0) + exit_val

    if exit_data:
        fig = go.Figure(go.Bar(
            x=[str(y) for y in sorted(exit_data.keys())],
            y=[exit_data[y] for y in sorted(exit_data.keys())],
            marker_color="#4c8bf5",
            text=[utils.fmt_eur(exit_data[y]) for y in sorted(exit_data.keys())],
            textposition="auto",
        ))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
                          xaxis_title="Exit Year", yaxis_title="Expected Value (EUR)",
                          yaxis=dict(tickformat=",.0f"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No active positions with scheduled exits.")

with tab2:
    st.subheader("Valuations (IRR × Probability)")
    st.caption("🟡 Actual = user-entered value (anchor for projections). ⚪ Formula = IRR × probability. "
               "All year cells are editable — edit to set actual values, set to 0 to clear an override.")

    scenario = st.selectbox("Scenario", utils.SCENARIOS, index=2, key="pe_proj_scenario")

    # All relevant items: Active + Exited (until exit year) + Written Off (with vh)
    val_items = utils._get_pe_valuation_items()

    # Build full timeline: from earliest investment year through current+10
    earliest_year = min((p.get("year_invested", utils.CURRENT_YEAR) for p in val_items), default=utils.CURRENT_YEAR)
    earliest_year = min(earliest_year, 2020)  # At least 2020
    proj_years = 10
    years_list = list(range(earliest_year, utils.CURRENT_YEAR + proj_years + 1))

    mult = utils.get_scenario_multipliers("pe", scenario)

    proj_rows = []
    totals_by_year = [0.0] * len(years_list)
    is_actual_map = {}  # (row_idx, yr_str) -> bool

    for row_idx, p in enumerate(val_items):
        status = p.get("status", "Active")
        exit_yr = p.get("expected_exit_year", 9999)
        current = p.get("current_value_eur", 0)
        year_invested = p.get("year_invested", 2000)
        irr = p.get("expected_irr_pct", 0) * mult["irr"]
        prob = min(100, p.get("success_probability_pct", 0) * mult["prob"])
        name_label = p.get("name", "")
        if status == "Exited":
            name_label += f" (exited {exit_yr})"
        elif status == "Written Off":
            name_label += " (written off)"
        row = {"Name": name_label, "Current": round(current),
               "IRR": f"{irr:.0f}%", "Prob": f"{prob:.0f}%",
               "Year In": year_invested}
        vh = p.get("value_history", {})
        prev_val = current
        for i, yr in enumerate(years_list):
            if yr < year_invested:
                row[str(yr)] = 0
                is_actual_map[(row_idx, str(yr))] = False
                continue
            if status == "Exited" and yr >= exit_yr:
                row[str(yr)] = 0
                is_actual_map[(row_idx, str(yr))] = False
                continue
            if status == "Written Off":
                override = vh.get(str(yr))
                val = override if override is not None and override > 0 else 0
                row[str(yr)] = round(val)
                totals_by_year[i] += val
                is_actual_map[(row_idx, str(yr))] = val > 0
                continue

            is_input = False
            override = vh.get(str(yr))
            has_override = override is not None and override > 0

            if has_override:
                val = override
                is_input = True
            elif yr == year_invested and not vh:
                val = p.get("amount_invested_eur", 0)
            elif i == 0 or prev_val == 0:
                val = 0
                for prev_yr in range(yr - 1, year_invested - 1, -1):
                    prev_override = vh.get(str(prev_yr))
                    if prev_override is not None and prev_override > 0:
                        val = prev_override * (1 + irr / 100) * (prob / 100)
                        break
                if val == 0 and yr >= year_invested:
                    val = current if current > 0 else p.get("amount_invested_eur", 0)
            else:
                if status == "Exited":
                    val = prev_val
                else:
                    val = prev_val * (1 + irr / 100) * (prob / 100) if prob > 0 else 0

            prev_val = val
            row[str(yr)] = round(val)
            totals_by_year[i] += val
            is_actual_map[(row_idx, str(yr))] = is_input
        proj_rows.append(row)

    # Total row
    total_row = {"Name": "TOTAL", "Current": 0, "IRR": "", "Prob": "", "Year In": 0}
    for i, yr in enumerate(years_list):
        total_row[str(yr)] = round(totals_by_year[i])
    proj_rows.append(total_row)

    proj_df = pd.DataFrame(proj_rows)
    orig_df = proj_df.copy()
    year_strs = [str(yr) for yr in years_list]

    row_height = min(500, max(250, len(proj_rows) * 32 + 40))
    st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — edit year cells to set actual values. Set to 0 to clear an override. Math expressions supported.</p>', unsafe_allow_html=True)

    col_config = {
        "Name": st.column_config.TextColumn("Name"),
        "Current": st.column_config.NumberColumn(format="€%.0f"),
        "Year In": st.column_config.NumberColumn(format="%d"),
    }
    for yr_str in year_strs:
        col_config[yr_str] = st.column_config.NumberColumn(format="€%.0f")

    edited_proj = st.data_editor(proj_df, use_container_width=True, hide_index=True,
        height=row_height, column_config=col_config,
        disabled=["Name", "Current", "IRR", "Prob", "Year In"], key="pe_valuation_editor")
    edited_proj = utils.process_math_in_df(edited_proj, year_strs)

    if st.button("💾 Save Valuations", type="primary", key="pe_save_valuations"):
        all_items = utils.load_json(utils.DATA_DIR / "private_equity.json", [])
        for row_idx, p in enumerate(val_items):
            name = p.get("name", "")
            for item in all_items:
                if item.get("name") == name:
                    vh = item.get("value_history", {})
                    for yr_str in year_strs:
                        new_val = float(edited_proj.iloc[row_idx].get(yr_str, 0) or 0)
                        orig_val = float(orig_df.iloc[row_idx].get(yr_str, 0) or 0)
                        if abs(new_val - orig_val) > 0.5:  # Cell was edited
                            if new_val > 0:
                                vh[yr_str] = new_val
                            else:
                                vh.pop(yr_str, None)
                    item["value_history"] = vh
                    # Update current_value from latest year with data
                    for yr in reversed(years_list):
                        if vh.get(str(yr), 0) > 0:
                            item["current_value_eur"] = vh[str(yr)]
                            break
                    if item.get("status") == "Exited":
                        for yr in reversed(years_list):
                            if vh.get(str(yr), 0) > 0:
                                item["exit_value_eur"] = vh[str(yr)]
                                break
                    break
        utils.save_json(utils.DATA_DIR / "private_equity.json", all_items)
        st.success("Valuations saved! Projections will update.")
        st.rerun()

    # Data source info
    with st.expander("ℹ️ Data Sources"):
        st.markdown("""
**Year-end values**
- 🟡 **Actual**: User-entered values stored as anchors in value_history. These override formula projections.
- ⚪ **Formula**: `V(N) = V(N-1) × (1 + IRR%) × (Probability%)`
- Edit any year cell to set an actual value. Set to 0 to remove an override.

**IRR & Probability**
- Per-item IRR from 💼 PE > Positions tab
- Scenario multipliers from ⚙️ FX & Settings > IRR-Based Asset Scenarios
- Current scenario: **{}** (IRR ×{:.2f}, Prob ×{:.2f})

**Actuals in this table:**
""".format(scenario, mult["irr"], mult["prob"]))
        # List which items have actuals for which years
        actual_summary = []
        for row_idx, p in enumerate(val_items):
            vh = p.get("value_history", {})
            actual_yrs = [yr for yr in sorted(vh.keys()) if vh[yr] > 0]
            if actual_yrs:
                actual_summary.append(f"- **{p.get('name', '')}**: {', '.join(actual_yrs)}")
        if actual_summary:
            st.markdown("\n".join(actual_summary))
        else:
            st.markdown("_No actual values entered yet._")

    # Chart
    fig_proj = go.Figure()
    actual_x, actual_y, proj_x, proj_y = [], [], [], []
    for i, yr in enumerate(years_list):
        if yr <= utils.CURRENT_YEAR and totals_by_year[i] > 0:
            actual_x.append(yr)
            actual_y.append(totals_by_year[i])
        elif totals_by_year[i] > 0:
            proj_x.append(yr)
            proj_y.append(totals_by_year[i])
    if actual_x:
        fig_proj.add_trace(go.Scatter(x=actual_x, y=actual_y, mode="lines+markers",
                                       line=dict(color="#f59e0b", width=3), name="Actual",
                                       text=[utils.fmt_eur(v) for v in actual_y],
                                       hovertemplate="%{x}: %{text}"))
    if proj_x:
        fig_proj.add_trace(go.Scatter(x=proj_x, y=proj_y, mode="lines+markers",
                                       line=dict(color="#60a5fa", width=2, dash="dot"), name="Projected",
                                       text=[utils.fmt_eur(v) for v in proj_y],
                                       hovertemplate="%{x}: %{text}"))
    fig_proj.update_layout(
        template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
        xaxis_title="Year", yaxis_title="Value (EUR)",
        yaxis=dict(tickformat=",.0f"), title=f"PE Valuation ({scenario})",
    )
    st.plotly_chart(fig_proj, use_container_width=True)
