import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("💰 Funds")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div.stDataFrame,div[data-testid="stDataEditor"]{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:4px}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)

items = utils.load_json(utils.DATA_DIR / "funds.json", [])
active = [i for i in items if i.get("status") == "Active"]

total_committed = sum(i.get("committed_eur", 0) for i in items)
total_called = sum(i.get("called_eur", 0) for i in items)

# Year-end value: use value_history for latest completed year
latest_yr = str(utils.CURRENT_YEAR - 1)
total_nav = 0
missing_items = []
for f in active:
    vh = f.get("value_history", {})
    val = vh.get(latest_yr, 0)
    if val <= 0:
        val = f.get("current_nav_eur", 0)
        missing_items.append(f.get("name", "Unknown"))
    total_nav += val
year_label = f" ({latest_yr} YE)"
missing_note = ""
if missing_items:
    missing_note = f' <span style="color:red">* {len(missing_items)} items without {latest_yr} valuation</span>'

c1, c2, c3 = st.columns(3)
c1.metric(f"Current NAV{year_label}", utils.fmt_eur(total_nav))
c2.metric("Total Committed", utils.fmt_eur(total_committed))
c3.metric("Total Called", utils.fmt_eur(total_called))
if missing_note:
    st.markdown(missing_note, unsafe_allow_html=True)

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Positions", "Capital Calls", "Future Valuations", "Edit"])

with tab1:
    if active:
        st.subheader(f"Active Funds ({len(active)})")
        rows = []
        for f in active:
            committed = f.get("committed_eur", 0)
            called = f.get("called_eur", 0)
            nav = f.get("current_nav_eur", 0)
            rows.append({
                "Name": f.get("name", ""),
                "Year": f.get("year_invested", ""),
                "Exit": str(f.get("expected_exit_year") or "Open"),
                "Committed": utils.fmt_eur_short(committed),
                "Called": utils.fmt_eur_short(called),
                "NAV": utils.fmt_eur_short(nav),
                "Called %": f"{called/committed*100:.0f}%" if committed > 0 else "0%",
                "IRR %": f"{f.get('expected_irr_pct', 0):.0f}%",
                "Access": f.get("access_layer", ""),
            })
        df_active = pd.DataFrame(rows)
        row_height = min(400, max(200, len(rows) * 32 + 40))
        utils.render_aggrid_table(df_active, key="aggrid_funds_active", height=row_height)

    closed = [i for i in items if i.get("status") == "Closed"]
    if closed:
        st.subheader(f"Closed ({len(closed)})")
        c_rows = []
        for f in closed:
            c_rows.append({
                "Name": f.get("name", ""),
                "Year In": f.get("year_invested", ""),
                "Committed": utils.fmt_eur_short(f.get("committed_eur", 0)),
                "Called": utils.fmt_eur_short(f.get("called_eur", 0)),
                "Final NAV": utils.fmt_eur_short(f.get("current_nav_eur", 0)),
            })
        utils.render_aggrid_table(pd.DataFrame(c_rows), key="aggrid_funds_closed", height=300)

with tab2:
    st.subheader("Capital Call Schedules")
    st.caption("Edit planned call % per year. Color: 🟢 95-100% total, 🔴 >100%, 🟡 <95%")

    for f in items:
        committed = f.get("committed_eur", 0)
        schedule = f.get("capital_call_schedule", [])
        if not schedule and not committed:
            continue

        with st.expander(f"📊 {f.get('name', '')} — Committed: {utils.fmt_eur_short(committed)}"):
            sched_rows = []
            for cs in schedule:
                yr = cs.get("year", 0)
                pct = cs.get("planned_pct", 0)
                actual = cs.get("actual_eur", 0)
                sched_rows.append({
                    "Year": yr,
                    "Planned %": pct,
                    "Planned EUR": utils.fmt_eur_short(committed * pct / 100) if committed > 0 else "€0",
                    "Actual EUR": actual,
                })

            if sched_rows:
                total_pct = sum(cs.get("planned_pct", 0) for cs in schedule)
                total_actual = sum(cs.get("actual_eur", 0) for cs in schedule)

                # Color indicator
                if total_pct > 100:
                    st.error(f"⚠️ Total planned: {total_pct:.1f}% (over 100%)")
                elif total_pct < 95:
                    st.warning(f"📉 Total planned: {total_pct:.1f}% (under 95%)")
                else:
                    st.success(f"✅ Total planned: {total_pct:.1f}%")

                sched_df = pd.DataFrame(sched_rows)
                st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter your values below</p>', unsafe_allow_html=True)
                st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
                sched_df = utils.inject_formulas_for_edit(sched_df, f"funds_calls_{f.get('id', '')}", ["Planned %", "Actual EUR"])
                edited_sched = st.data_editor(sched_df, use_container_width=True, hide_index=True,
                    num_rows="dynamic", key=f"calls_{f.get('id', '')}",
                    column_config={
                        "Year": st.column_config.NumberColumn(format="%d"),
                        "Planned %": st.column_config.NumberColumn(format="%.1f%%"),
                        "Actual EUR": st.column_config.NumberColumn(format="€%.0f"),
                        "Planned EUR": st.column_config.TextColumn(disabled=True),
                    })
                edited_sched = utils.process_math_in_df(edited_sched, ["Planned %", "Actual EUR"], editor_key=f"funds_calls_{f.get('id', '')}")

                if st.button(f"Save {f.get('name', '')}", key=f"save_calls_{f.get('id', '')}"):
                    new_sched = []
                    for _, row in edited_sched.iterrows():
                        if pd.notna(row.get("Year")):
                            new_sched.append({
                                "year": int(row["Year"]),
                                "planned_pct": float(row.get("Planned %", 0) or 0),
                                "actual_eur": float(row.get("Actual EUR", 0) or 0),
                            })
                    all_funds = utils.load_json(utils.DATA_DIR / "funds.json", [])
                    for uf in all_funds:
                        if uf.get("id") == f.get("id"):
                            uf["capital_call_schedule"] = new_sched
                            # Update called_eur from actuals up to current year
                            uf["called_eur"] = sum(
                                s["actual_eur"] for s in new_sched
                                if s["year"] <= utils.CURRENT_YEAR
                            )
                    utils.save_json(utils.DATA_DIR / "funds.json", all_funds)
                    st.success("Schedule saved!")
                    st.rerun()

    # Aggregated cashflow chart
    st.subheader("Aggregated Fund Cash Flows")
    agg = {}
    for f in items:
        for cs in f.get("capital_call_schedule", []):
            yr = cs.get("year")
            if yr:
                agg.setdefault(yr, 0)
                agg[yr] += cs.get("actual_eur", 0)
    if agg:
        years_sorted = sorted(agg.keys())
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[str(y) for y in years_sorted],
            y=[-agg[y] for y in years_sorted],
            name="Capital Calls",
            marker_color="#ff4444",
            text=[utils.fmt_eur(agg[y]) for y in years_sorted],
            textposition="auto",
        ))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
                          xaxis_title="Year", yaxis_title="EUR", title="Capital Calls by Year")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Future Valuations (IRR Growth)")
    st.caption("🟡 Actual = user-entered NAV. ⚪ Formula = V(N-1) × (1 + IRR) + new_call(N). "
               "All year cells are editable — edit to set actual values, set to 0 to clear.")

    scenario = st.selectbox("Scenario", utils.SCENARIOS, index=2, key="fund_proj_scenario")
    proj_years = 10
    base_year = utils.get_base_year() or (utils.CURRENT_YEAR - 2)
    years_list = list(range(base_year, base_year + proj_years + 1))

    mult = utils.get_scenario_multipliers("pe", scenario)
    irr_mult = mult["irr"]

    proj_rows = []
    totals_by_year = [0.0] * (proj_years + 1)

    for row_idx, f in enumerate(active):
        irr = f.get("expected_irr_pct", 0) * irr_mult / 100
        year_invested = f.get("year_invested", 2020)
        committed = f.get("committed_eur", 0)
        vh = f.get("value_history", {})
        schedule = {cs["year"]: cs.get("actual_eur", 0) for cs in f.get("capital_call_schedule", [])}

        row = {
            "Name": f.get("name", ""),
            "IRR": f"{f.get('expected_irr_pct', 0) * irr_mult:.0f}%",
            "Exit": str(f.get("expected_exit_year") or "Open"),
        }

        prev_val = f.get("current_nav_eur", 0)
        for i, yr in enumerate(years_list):
            if yr < year_invested:
                row[str(yr)] = 0
                continue

            override = vh.get(str(yr))
            has_override = override is not None and override > 0

            if i == 0 or yr == year_invested:
                if has_override:
                    val = override
                else:
                    val = vh.get(str(yr), prev_val) or prev_val
            else:
                if has_override:
                    val = override
                else:
                    new_call = schedule.get(yr, 0)
                    val = prev_val * (1 + irr) + new_call

            exit_yr = f.get("expected_exit_year")
            if exit_yr and yr > exit_yr:
                val = 0

            prev_val = val
            row[str(yr)] = round(val)
            totals_by_year[i] += val

        proj_rows.append(row)

    # Total row
    funds_totals = utils.compute_funds_timeline(years_list, scenario)
    total_row = {"Name": "TOTAL", "IRR": "", "Exit": ""}
    for i, yr in enumerate(years_list):
        total_row[str(yr)] = round(funds_totals[i])
    proj_rows.append(total_row)

    proj_df = pd.DataFrame(proj_rows)
    orig_df = proj_df.copy()
    year_strs = [str(yr) for yr in years_list]
    row_height = min(500, max(250, len(proj_rows) * 32 + 40))

    st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — edit year cells to set actual NAV values. Set to 0 to clear. Math expressions supported.</p>', unsafe_allow_html=True)

    col_config = {"Name": st.column_config.TextColumn("Name")}
    for yr_str in year_strs:
        col_config[yr_str] = st.column_config.NumberColumn(format="€%.0f")

    proj_df = utils.inject_formulas_for_edit(proj_df, "funds_valuations", year_strs)
    edited_proj = st.data_editor(proj_df, use_container_width=True, hide_index=True,
        height=row_height, column_config=col_config,
        disabled=["Name", "IRR", "Exit"], key="fund_valuation_editor")
    edited_proj = utils.process_math_in_df(edited_proj, year_strs, editor_key="funds_valuations")

    if st.button("💾 Save Valuations", type="primary", key="fund_save_valuations"):
        all_funds = utils.load_json(utils.DATA_DIR / "funds.json", [])
        for row_idx, f in enumerate(active):
            name = f.get("name", "")
            for fund in all_funds:
                if fund.get("name") == name:
                    vh = fund.get("value_history", {})
                    for yr_str in year_strs:
                        new_val = float(edited_proj.iloc[row_idx].get(yr_str, 0) or 0)
                        orig_val = float(orig_df.iloc[row_idx].get(yr_str, 0) or 0)
                        if abs(new_val - orig_val) > 0.5:
                            if new_val > 0:
                                vh[yr_str] = new_val
                            else:
                                vh.pop(yr_str, None)
                    fund["value_history"] = vh
                    for yr in reversed(years_list):
                        if vh.get(str(yr), 0) > 0:
                            fund["current_nav_eur"] = vh[str(yr)]
                            break
                    break
        utils.save_json(utils.DATA_DIR / "funds.json", all_funds)
        st.success("Valuations saved!")
        st.rerun()

    # Data source info
    with st.expander("ℹ️ Data Sources"):
        st.markdown("""
**Year-end NAV**
- 🟡 **Actual**: User-entered values stored as anchors
- ⚪ **Formula**: `V(N) = V(N-1) × (1 + IRR%) + Capital Call(N)`
- Edit any year cell to set an actual value. Set to 0 to remove.

**IRR & Scenario**
- Per-fund IRR from 💰 Funds > Positions tab
- Scenario multiplier from ⚙️ FX & Settings > IRR-Based Asset Scenarios
- Current scenario: **{}** (IRR ×{:.2f})

**Actuals in this table:**
""".format(scenario, irr_mult))
        actual_summary = []
        for f in active:
            vh = f.get("value_history", {})
            actual_yrs = [yr for yr in sorted(vh.keys()) if vh[yr] > 0]
            if actual_yrs:
                actual_summary.append(f"- **{f.get('name', '')}**: {', '.join(actual_yrs)}")
        if actual_summary:
            st.markdown("\n".join(actual_summary))
        else:
            st.markdown("_No actual values entered yet._")

    # Chart
    fig_proj = go.Figure()
    fig_proj.add_trace(go.Scatter(
        x=years_list, y=funds_totals,
        mode="lines+markers", line=dict(color="#4c8bf5", width=3),
        name="Total Funds (projected)",
        text=[utils.fmt_eur(v) for v in funds_totals],
        hovertemplate="%{x}: %{text}",
    ))
    fig_proj.update_layout(
        template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
        xaxis_title="Year", yaxis_title="Value (EUR)",
        yaxis=dict(tickformat=",.0f"), title=f"Fund Projections ({scenario})",
    )
    st.plotly_chart(fig_proj, use_container_width=True)

with tab4:
    st.subheader("Edit Funds")
    edit_rows = [{
        "name": f.get("name", ""),
        "year_invested": f.get("year_invested", 2024),
        "expected_exit_year": f.get("expected_exit_year") or 0,
        "committed_eur": f.get("committed_eur", 0),
        "called_eur": f.get("called_eur", 0),
        "current_nav_eur": f.get("current_nav_eur", 0),
        "expected_irr_pct": f.get("expected_irr_pct", 0),
        "access_layer": f.get("access_layer", "Direct"),
        "status": f.get("status", "Active"),
        "notes": f.get("notes", ""),
    } for f in items]

    edit_df = pd.DataFrame(edit_rows) if edit_rows else pd.DataFrame(
        columns=["name", "year_invested", "expected_exit_year", "committed_eur",
                 "called_eur", "current_nav_eur", "expected_irr_pct",
                 "access_layer", "status", "notes"])

    row_height = min(400, max(200, len(edit_rows) * 32 + 40))
    st.markdown('<p style="background:#1b4332;color:#a7f3d0;padding:4px 12px;border-radius:4px;font-size:0.85em;margin:0">✏️ Editable — enter your values below</p>', unsafe_allow_html=True)
    st.caption("💡 Supports math expressions (e.g. 500*2) and FX shortcuts (e.g. 1000/EURUSD)")
    edit_df = utils.inject_formulas_for_edit(edit_df, "funds_holdings", ["committed_eur", "called_eur", "current_nav_eur", "expected_irr_pct"])
    edited = st.data_editor(edit_df, use_container_width=True, hide_index=True, num_rows="dynamic",
        height=row_height,
        column_config={
            "access_layer": st.column_config.SelectboxColumn("Access", options=["Direct", "LA", "ECI"]),
            "status": st.column_config.SelectboxColumn("Status", options=["Active", "Closed"]),
            "committed_eur": st.column_config.NumberColumn("Committed", format="€%.0f"),
            "called_eur": st.column_config.NumberColumn("Called", format="€%.0f"),
            "current_nav_eur": st.column_config.NumberColumn("NAV", format="€%.0f"),
            "expected_irr_pct": st.column_config.NumberColumn("IRR %", format="%.1f%%"),
            "expected_exit_year": st.column_config.NumberColumn("Exit Year", format="%d"),
        })
    edited = utils.process_math_in_df(edited, ["committed_eur", "called_eur", "current_nav_eur", "expected_irr_pct"], editor_key="funds_holdings")

    if st.button("💾 Save Funds", type="primary", key="funds_save"):
        new_items = []
        for j, (_, row) in enumerate(edited.iterrows()):
            if row.get("name"):
                orig = items[j] if j < len(items) else {}
                exit_yr = int(row.get("expected_exit_year", 0) or 0)
                new_items.append({
                    "id": orig.get("id", utils.new_id()),
                    "name": row["name"],
                    "year_invested": int(row.get("year_invested", 2024) or 2024),
                    "expected_exit_year": exit_yr if exit_yr > 2000 else None,
                    "committed_eur": float(row.get("committed_eur", 0) or 0),
                    "called_eur": float(row.get("called_eur", 0) or 0),
                    "current_nav_eur": float(row.get("current_nav_eur", 0) or 0),
                    "expected_irr_pct": float(row.get("expected_irr_pct", 0) or 0),
                    "access_layer": row.get("access_layer", "Direct"),
                    "status": row.get("status", "Active"),
                    "notes": row.get("notes", ""),
                    "capital_call_schedule": orig.get("capital_call_schedule", []),
                    "value_history": orig.get("value_history", {}),
                })
        utils.save_json(utils.DATA_DIR / "funds.json", new_items)
        st.success("Saved!")
        st.rerun()
