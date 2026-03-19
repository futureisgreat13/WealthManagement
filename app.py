import streamlit as st
import json
import hashlib
import base64
import os
import requests
from pathlib import Path
from datetime import datetime, timedelta
from utils import setup_user_data_dir, auto_refresh_fx_rates, auto_refresh_stock_prices, get_live_market_data

st.set_page_config(
    page_title="Wealth Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Google OAuth with PKCE ──────────────────────────────────────────
CLIENT_ID     = st.secrets["google_auth"]["client_id"]
CLIENT_SECRET = st.secrets["google_auth"]["client_secret"]
REDIRECT_URI  = st.secrets["google_auth"]["redirect_uri"]
AUTH_URL       = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL      = "https://oauth2.googleapis.com/token"
USERINFO_URL   = "https://www.googleapis.com/oauth2/v2/userinfo"
SCOPES         = "openid email profile"

# Directory to persist PKCE verifiers across redirects
_PKCE_DIR = Path(__file__).parent / ".streamlit" / "_pkce"
_PKCE_DIR.mkdir(parents=True, exist_ok=True)

# Directory for persistent sessions (survives page refresh)
_SESSION_DIR = Path(__file__).parent / ".streamlit" / "_sessions"
_SESSION_DIR.mkdir(parents=True, exist_ok=True)


def _generate_pkce():
    """Generate PKCE code_verifier and code_challenge."""
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def _get_authorization_url():
    """Build Google OAuth authorization URL with PKCE, persisted via state token."""
    verifier, challenge = _generate_pkce()
    state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode()
    # Persist verifier to disk keyed by state (survives redirect)
    (_PKCE_DIR / state).write_text(verifier)
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    qs = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{AUTH_URL}?{qs}"


def _exchange_code(code: str, state: str) -> dict:
    """Exchange authorization code for user info, using persisted PKCE verifier."""
    # Retrieve verifier from disk
    verifier_file = _PKCE_DIR / state
    if not verifier_file.exists():
        st.error("Login session expired. Please try signing in again.")
        return {}
    verifier = verifier_file.read_text()
    verifier_file.unlink()  # Clean up after use

    resp = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    })
    if resp.status_code != 200:
        st.error(f"Token exchange failed: {resp.text}")
        return {}
    token = resp.json()
    # Fetch user profile
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    user_resp = requests.get(USERINFO_URL, headers=headers)
    if user_resp.status_code != 200:
        st.error(f"Failed to get user info: {user_resp.text}")
        return {}
    return user_resp.json()


# ── File-based session persistence ─────────────────────────────────
def _save_session(user_info: dict):
    """Save user session to disk so it survives page refresh & server restart."""
    session_data = {
        "email": user_info["email"],
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
        "created": datetime.now().isoformat(),
        "expires": (datetime.now() + timedelta(days=30)).isoformat(),
    }
    session_file = _SESSION_DIR / "active_session.json"
    session_file.write_text(json.dumps(session_data, indent=2))


def _load_session() -> dict:
    """Load saved session from disk. Returns user_info dict or empty dict."""
    session_file = _SESSION_DIR / "active_session.json"
    if not session_file.exists():
        return {}
    try:
        data = json.loads(session_file.read_text())
        # Check expiry
        if datetime.fromisoformat(data["expires"]) < datetime.now():
            session_file.unlink()
            return {}
        return data
    except (json.JSONDecodeError, KeyError, ValueError):
        return {}


def _clear_session():
    """Delete saved session on sign out."""
    session_file = _SESSION_DIR / "active_session.json"
    if session_file.exists():
        session_file.unlink()


# ── Auth check ──────────────────────────────────────────────────────
if "connected" not in st.session_state:
    st.session_state["connected"] = False

# Check for OAuth callback code
auth_code = st.query_params.get("code")
auth_state = st.query_params.get("state", "")
if auth_code and not st.session_state["connected"]:
    st.query_params.clear()
    user_info = _exchange_code(auth_code, auth_state)
    if user_info and user_info.get("email"):
        st.session_state["connected"] = True
        st.session_state["user_info"] = {
            "email": user_info["email"],
            "name": user_info.get("name", ""),
            "picture": user_info.get("picture", ""),
        }
        # Persist session to disk so it survives page refresh
        _save_session(user_info)
        st.rerun()

# Check for existing session on disk (persistent login across refreshes)
if not st.session_state["connected"]:
    saved = _load_session()
    if saved:
        st.session_state["connected"] = True
        st.session_state["user_info"] = {
            "email": saved["email"],
            "name": saved.get("name", ""),
            "picture": saved.get("picture", ""),
        }
        st.rerun()

# ── Define navigation (must be before st.stop() to prevent auto-discovery) ──
if "scenario" not in st.session_state:
    st.session_state.scenario = "Base"

pages = {
    "": [st.Page("pages/overview.py", title="Overview", icon="🏠")],
    "Liquid Assets": [
        st.Page("pages/public_stocks.py", title="Equity",           icon="📈"),
        st.Page("pages/reits.py",          title="REITs",            icon="🏢"),
        st.Page("pages/bonds.py",          title="Bonds",            icon="📄"),
        st.Page("pages/precious_metals.py", title="Precious Metals", icon="🥇"),
        st.Page("pages/cashflow.py",       title="Cash Flow",        icon="💸"),
    ],
    "Illiquid Assets": [
        st.Page("pages/real_estate.py",    title="Real Estate",      icon="🏠"),
        st.Page("pages/private_equity.py", title="Private Equity",   icon="💼"),
        st.Page("pages/funds.py",          title="Funds",            icon="💰"),
        st.Page("pages/business.py",       title="Business",         icon="🏭"),
        st.Page("pages/debt.py",           title="Debt",             icon="📉"),
    ],
    "Planning": [
        st.Page("pages/year_end.py",         title="Year-End Checklist",     icon="✅"),
        st.Page("pages/investment_plan.py",  title="Investment Plan",         icon="📊"),
        st.Page("pages/ibkr_import.py",      title="IBKR Import",            icon="📥"),
        st.Page("pages/symbol_classifications.py", title="Symbol Classifications", icon="🏷️"),
        st.Page("pages/todo.py",            title="To Do",                    icon="📝"),
        st.Page("pages/rules.py",           title="Rules & Docs",            icon="📖"),
        st.Page("pages/fx_settings.py",     title="FX & Settings",           icon="⚙️"),
    ],
}
nav = st.navigation(pages)

# ── Login page ──────────────────────────────────────────────────────
if not st.session_state["connected"]:
    auth_url = _get_authorization_url()
    st.markdown(
        "<h1 style='text-align:center; margin-top:15vh;'>💎 Wealth Dashboard</h1>"
        "<p style='text-align:center; color:#888;'>Sign in with your Google account to continue.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(f"""
<div style="display:flex; justify-content:center; margin-top:2rem;">
    <a href="{auth_url}" onclick="window.top.location.href=this.href; return false;" style="background-color:#4285f4; color:#fff; text-decoration:none;
       text-align:center; font-size:16px; padding:10px 20px; border-radius:4px; display:flex; align-items:center; cursor:pointer;">
        <img src="https://lh3.googleusercontent.com/COxitqgJr1sJnIDe8-jiKhxDx1FrYbtRHKJ9z_hELisAlapwE9LUPh6fcXIfb5vwpbMl4xl9H9TRFPc5NOO8Sb3VSgIBrfRYvW6cUA"
             alt="G" style="margin-right:8px; width:24px; height:24px; background:white; border:2px solid white; border-radius:4px;">
        Sign in with Google
    </a>
</div>
""", unsafe_allow_html=True)
    st.stop()

# ── User is authenticated ──────────────────────────────────────────
user_email = st.session_state["user_info"]["email"]
user_name  = st.session_state["user_info"].get("name", "")
user_dir   = setup_user_data_dir(user_email, user_name)

# Load profile to check onboarding
profile_path = user_dir / "_profile.json"
profile = {}
if profile_path.exists():
    with open(profile_path, "r") as f:
        profile = json.load(f)

# ── First-login onboarding ─────────────────────────────────────────
if not profile.get("onboarding_complete"):
    st.markdown(
        f'<h1 style="text-align:center;margin-top:1em">Welcome, {user_name or user_email}! 👋</h1>'
        '<p style="text-align:center;color:#888;font-size:1.1em">'
        'Your personal Wealth Dashboard is ready. Here\'s everything you need to know.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    # ── What is this app? ──
    st.markdown("## 💎 What is this app?")
    st.markdown("""
A **personal wealth management dashboard** that gives you a complete picture of your finances in one place.
Track every asset you own, see how your net worth changes over time, and plan for the future with
scenario-based projections. Think of it as your own Bloomberg terminal — but simpler and built for you.

**Everything is in EUR.** All values from other currencies are automatically converted using live exchange rates.
""")
    st.divider()

    # ── Your Asset Classes ──
    st.markdown("## 📊 What can you track?")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
**Liquid Assets** *(easy to sell)*
- **Equity** — Public stocks & ETFs
- **REITs** — Real estate investment trusts
- **Bonds** — Fixed income
- **Precious Metals** — Gold, silver, etc.
- **Cash** — Bank accounts & savings
""")
    with col2:
        st.markdown("""
**Illiquid Assets** *(harder to sell)*
- **Real Estate** — Properties you own
- **Private Equity** — PE fund investments
- **Funds** — VC / growth funds
- **Business** — Business ownership stakes
- **Debt** — Loans & mortgages (tracked as negative)
""")
    st.divider()

    # ── How it works ──
    st.markdown("## 🔧 How does it work?")
    st.markdown("""
**1. Enter your assets**
Use the sidebar to navigate to each asset class. Add your positions — name, amount invested, current value.
Tables are editable: just click a cell and type. You can use math expressions like `=500*2` or `=1000/EURUSD`.

**2. Understand the colors**
- 🟡 **Yellow cells** = values YOU entered (manual input)
- 🔵 **Blue cells** = imported from Interactive Brokers
- ⚪ **White cells** = calculated automatically by formulas

**3. Year-end updates**
At the end of each year, update your actual asset values. The app will remind you what's missing.
Go to **Year-End Checklist** in the sidebar to see what still needs updating.

**4. See your portfolio**
The **Overview** page shows your total net worth, asset allocation, and multi-year projections
under different scenarios (Bull, Base, Bear, Super Bear).

**5. Projections & Planning**
Future values are projected using growth rates and scenario multipliers.
Use **Investment Plan** to set target allocations and planned annual investments per asset class.
""")
    st.divider()

    # ── Scenarios ──
    st.markdown("## 📈 Scenarios")
    st.markdown("""
The app projects your portfolio under **4 scenarios** to help you plan for different market conditions:

| Scenario | What it means |
|----------|---------------|
| **Bull** | Markets do better than expected |
| **Base** | Most likely outcome |
| **Bear** | Markets underperform |
| **Super Bear** | Severe downturn |

Each asset class has its own scenario multipliers (e.g. equity growth rates, real estate appreciation, PE IRR).
You can customize these in the settings.
""")
    st.divider()

    # ── Cash Flow ──
    st.markdown("## 💰 Cash Flow")
    st.markdown("""
Track where your money comes from and where it goes:
- **Income**: Salary, dividends, rental income, business distributions
- **Expenses**: Living costs, debt payments, new investments

The **Cash Flow** page shows your annual net cash flow and helps you understand
how much free capital you have for new investments each year.
""")
    st.divider()

    # ── Quick tips ──
    st.markdown("## ⚡ Quick tips")
    st.markdown("""
- **FX rates update automatically** — live rates are fetched when you open the app
- **Math in cells** — type `=100000*1.05` or `=500/EURUSD` in any editable cell
- **Delete rows** — hover over a row in an editable table, click the minus icon, then save
- **Import from IBKR** — upload your Interactive Brokers CSV to auto-populate stock positions
- **All data is private** — each user has their own isolated data, nobody else can see yours
""")

    st.divider()
    st.markdown("")
    if st.button("🚀 Get Started", type="primary", use_container_width=True):
        profile["onboarding_complete"] = True
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)
        st.rerun()
    st.stop()

# ── Sidebar user info ──────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{user_name}**")
    st.caption(user_email)
    if st.button("Sign Out", use_container_width=True):
        _clear_session()
        st.session_state["connected"] = False
        st.session_state.pop("user_info", None)
        st.session_state.pop("user_data_dir", None)
        st.rerun()

# Auto-refresh market data (runs on every app load, throttled to 15 min)
# Wrapped in try/except to prevent page hangs on Cloud
try:
    auto_refresh_fx_rates()
except Exception:
    pass
try:
    auto_refresh_stock_prices()
except Exception:
    pass
try:
    get_live_market_data()
except Exception:
    pass

nav.run()
