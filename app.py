import streamlit as st

st.set_page_config(
    page_title="Wealth Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "scenario" not in st.session_state:
    st.session_state.scenario = "Base"

pages = {
    "": [st.Page("pages/overview.py", title="Overview", icon="🏠")],
    "Liquid Assets": [
        st.Page("pages/public_stocks.py", title="Equity", icon="📈"),
        st.Page("pages/reits.py",          title="REITs",               icon="🏢"),
        st.Page("pages/bonds.py",          title="Bonds",               icon="📄"),
        st.Page("pages/precious_metals.py", title="Precious Metals",    icon="🥇"),
        st.Page("pages/cashflow.py",       title="Cash Flow",           icon="💸"),
    ],
    "Illiquid Assets": [
        st.Page("pages/real_estate.py",    title="Real Estate",         icon="🏠"),
        st.Page("pages/private_equity.py", title="Private Equity",      icon="💼"),
        st.Page("pages/funds.py",          title="Funds",               icon="💰"),
        st.Page("pages/business.py",       title="Business",            icon="🏭"),
        st.Page("pages/debt.py",           title="Debt",                icon="📉"),
    ],
    "Planning": [
        st.Page("pages/investment_plan.py",  title="Investment Plan",    icon="📊"),
        st.Page("pages/ibkr_import.py",     title="IBKR Import",        icon="📥"),
        st.Page("pages/symbol_classifications.py", title="Symbol Classifications", icon="🏷️"),
        st.Page("pages/todo.py",            title="To Do",              icon="📝"),
        st.Page("pages/rules.py",           title="Rules & Docs",       icon="📖"),
        st.Page("pages/fx_settings.py",     title="FX & Settings",      icon="⚙️"),
    ],
}

st.navigation(pages).run()
