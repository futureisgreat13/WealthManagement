import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

st.title("Year-End Checklist")
st.caption("Track year-end data completeness across all asset classes. "
           "Missing data affects net worth accuracy, cash flow calculations, and projection anchoring.")

# Start from the user's first investment year (or CURRENT_YEAR - 2 if no data)
base_year = utils.get_base_year()
first_year = base_year if base_year else utils.CURRENT_YEAR - 1
check_years = list(range(first_year, utils.CURRENT_YEAR + 1))

for yr in check_years:
    comp = utils.get_year_end_completeness(yr)
    done = comp["complete_count"]
    total = comp["total_count"]
    missing = comp["missing_items"]
    complete = comp["complete_items"]
    pct = done / total if total > 0 else 0
    all_done = len(missing) == 0

    # Most critical year (CY-1) expanded by default when incomplete
    is_critical = (yr == utils.CURRENT_YEAR - 1)
    default_expanded = is_critical and not all_done

    label = f"{'✅' if all_done else '⚠️'} {yr} — {done}/{total} complete"
    if all_done:
        label = f"✅ {yr} — Complete ({done}/{done})"

    with st.expander(label, expanded=default_expanded):
        st.progress(pct, text=f"{done}/{total} items complete")

        # Group all items by asset class
        all_items = [(item, True) for item in complete] + [(item, False) for item in missing]
        grouped: dict[str, list] = {}
        for item, is_complete in all_items:
            ac = item["asset_class"]
            grouped.setdefault(ac, []).append((item, is_complete))

        # Order: missing-heavy groups first
        group_order = sorted(grouped.keys(),
                             key=lambda ac: sum(1 for _, ok in grouped[ac] if not ok), reverse=True)

        for ac in group_order:
            items = grouped[ac]
            ac_missing = sum(1 for _, ok in items if not ok)
            ac_icon = "✅" if ac_missing == 0 else "❌"
            st.markdown(f"**{ac_icon} {ac}**")

            for item, is_complete in items:
                icon = "✅" if is_complete else "❌"
                reason = utils.YEAR_END_REASONS.get(item["field"], "")
                if item["field"].endswith(f"for {yr}"):
                    # Expense items have year in field name, use base reason
                    reason = "Expense tracking & cash flow"
                reason_text = f" — *{reason}*" if reason else ""
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} {item['name']}: {item['field']}{reason_text}")
