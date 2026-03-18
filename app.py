import streamlit as st
import json
import hashlib
import base64
import os
import requests
from pathlib import Path
from datetime import datetime, timedelta
from utils import setup_user_data_dir, auto_refresh_fx_rates, auto_refresh_stock_prices

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
    <a href="{auth_url}" target="_self" style="background-color:#4285f4; color:#fff; text-decoration:none;
       text-align:center; font-size:16px; padding:10px 20px; border-radius:4px; display:flex; align-items:center;">
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
    st.markdown(f"# Welcome, {user_name or user_email}! 👋")
    st.markdown("### Your personal Wealth Dashboard is ready.")
    st.markdown("""
This dashboard helps you track and project your investments across multiple asset classes
with scenario analysis, cash flow management, and investment planning.

**Here's how to get started:**

1. **FX & Settings** — Set your currency exchange rates (all values are normalized to EUR)
2. **Add your assets** — Use the sidebar to navigate to each asset class:
   - **Liquid**: Equity, REITs, Bonds, Precious Metals
   - **Illiquid**: Real Estate, Private Equity, Funds, Business, Debt
3. **Cash Flow** — Track income and expenses
4. **Overview** — See your full portfolio summary and projections
5. **IBKR Import** — Import positions from Interactive Brokers (optional)

Each page has editable tables — yellow cells are for your input, white cells are calculated.
""")
    if st.button("Get Started", type="primary", use_container_width=True):
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
auto_refresh_fx_rates()
auto_refresh_stock_prices()

nav.run()
