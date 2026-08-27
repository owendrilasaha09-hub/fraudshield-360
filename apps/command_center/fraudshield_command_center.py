import re as _re
import base64 as _base64
import html as _html
import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session


def _rerun():
    """Version-safe rerun (st.rerun on newer Streamlit, experimental_rerun on older)."""
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass

session = get_active_session()

st.set_page_config(page_title="FraudShield Command Center", layout="wide")


# =============================================================================
# ROLE-BASED ACCESS CONTROL (RBAC) — Application-level authorization
# =============================================================================
ALLOWED_ROLES = {
    'FRAUD_ANALYST_ROLE',
    'COMPLIANCE_OFFICER_ROLE',
    'AUDIT_ROLE',
    'FRAUDSHIELD_ACCESS_ADMIN_ROLE',
}


def _validate_identifier(x):
    """Raise ValueError if x is not a safe SQL identifier."""
    if not x or not _re.match(r'^[A-Za-z0-9_]{1,255}$', str(x)):
        raise ValueError(f"Invalid identifier: {repr(x)}")
    return str(x)


def get_effective_roles(session):
    """Fetch active, non-expired roles for the current user from USER_ROLE_MAPPING."""
    try:
        roles_df = session.sql("""
            SELECT ASSIGNED_ROLE
            FROM FRAUDSHIELD_360_DB.AGENTS.USER_ROLE_MAPPING
            WHERE USER_NAME = CURRENT_USER()
              AND STATUS = 'ACTIVE'
              AND (EXPIRES_AT IS NULL OR EXPIRES_AT > CURRENT_TIMESTAMP())
        """).to_pandas()
        return roles_df["ASSIGNED_ROLE"].tolist() if not roles_df.empty else []
    except Exception:
        return []


ROLES = get_effective_roles(session)


def require(role):
    """Check if the current user holds a specific role."""
    return role in ROLES


# Gate: no roles = no access
if not ROLES:
    st.error("No access assigned to your account. Contact your administrator.")
    st.stop()

# Determine read-only mode (AUDIT_ROLE only, no other roles)
IS_READ_ONLY = (set(ROLES) == {"AUDIT_ROLE"})

# =============================================================================
# ENTERPRISE DESIGN SYSTEM  —  Snowflake-inspired UI theme
# Colors, typography, spacing and components aligned to the Snowflake brand:
#   Star Blue #29B5E8 · Mid Blue #11567F · Midnight Navy #1B3139
# NOTE: This block is purely presentational — no app logic is affected.
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --sf-blue:      #29B5E8;
        --sf-blue-deep: #11567F;
        --sf-navy:      #1B3139;
        --sf-navy-2:    #23424D;
        --sf-ink:       #16242B;
        --sf-slate:     #5B6B73;
        --sf-line:      #E3E9ED;
        --sf-surface:   #FFFFFF;
        --sf-canvas:    #F4F7F9;
        --sf-success:   #17916B;
        --sf-warning:   #C77700;
        --sf-danger:    #D92D20;
        --sf-radius:    14px;
        --sf-shadow:    0 1px 2px rgba(16,36,43,.04), 0 6px 20px rgba(16,36,43,.06);
    }

    /* ---- Global canvas & typography ---- */
    html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: var(--sf-ink);
    }
    .stApp { background: var(--sf-canvas); }
    .block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1400px; }

    /* ---- Hero header ---- */
    .sf-hero {
        position: relative;
        border-radius: 18px;
        padding: 26px 30px;
        margin-bottom: 22px;
        background: linear-gradient(120deg, #0E2A36 0%, #11567F 55%, #29B5E8 140%);
        box-shadow: 0 10px 30px rgba(17,86,127,.28);
        overflow: hidden;
    }
    .sf-hero::after {
        content: ""; position: absolute; top: -60px; right: -40px;
        width: 260px; height: 260px; border-radius: 50%;
        background: radial-gradient(circle, rgba(41,181,232,.45) 0%, rgba(41,181,232,0) 70%);
    }
    .sf-hero-row { display: flex; align-items: center; gap: 18px; position: relative; z-index: 1; }
    .sf-hero-mark {
        width: 54px; height: 54px; border-radius: 14px; flex: 0 0 auto;
        display: flex; align-items: center; justify-content: center;
        background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.25);
        font-size: 28px;
    }
    .sf-hero-title { color: #fff; font-size: 1.55rem; font-weight: 800; letter-spacing: -.02em; margin: 0; line-height: 1.1; }
    .sf-hero-sub { color: rgba(255,255,255,.82); font-size: .95rem; font-weight: 500; margin: 4px 0 0 0; }
    .sf-hero-pills { margin-left: auto; display: flex; gap: 8px; position: relative; z-index: 1; }
    .sf-pill {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.22);
        color: #fff; font-size: .78rem; font-weight: 600;
        padding: 6px 12px; border-radius: 999px;
    }
    .sf-dot { width: 8px; height: 8px; border-radius: 50%; background: #35E08F; box-shadow: 0 0 0 3px rgba(53,224,143,.25); }

    /* ---- Section headers (st.header / st.subheader) ---- */
    h1, h2, h3 { font-family: 'Inter', sans-serif; letter-spacing: -.01em; color: var(--sf-ink); }
    [data-testid="stHeader"] { background: transparent; }
    h2 {
        font-size: 1.28rem !important; font-weight: 700 !important;
        padding-left: 12px; margin-top: .2rem !important;
        border-left: 4px solid var(--sf-blue);
    }
    h3 { font-size: 1.05rem !important; font-weight: 700 !important; color: var(--sf-navy) !important; }

    /* ---- Metric cards (native st.metric styled as premium KPI tiles) ---- */
    [data-testid="stMetric"], [data-testid="metric-container"] {
        background: var(--sf-surface);
        border: 1px solid var(--sf-line);
        border-radius: var(--sf-radius);
        padding: 16px 18px 14px 18px;
        box-shadow: var(--sf-shadow);
        position: relative;
        overflow: hidden;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    [data-testid="stMetric"]::before, [data-testid="metric-container"]::before {
        content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
        background: linear-gradient(180deg, var(--sf-blue), var(--sf-blue-deep));
    }
    [data-testid="stMetric"]:hover, [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(16,36,43,.06), 0 14px 30px rgba(16,36,43,.10);
    }
    [data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] {
        font-size: .74rem !important; font-weight: 600 !important;
        text-transform: uppercase; letter-spacing: .06em; color: var(--sf-slate) !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.55rem !important; font-weight: 800 !important; color: var(--sf-navy) !important;
        line-height: 1.15;
    }

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #16242B 0%, #1B3139 60%, #16333D 100%);
        border-right: 1px solid rgba(255,255,255,.06);
    }
    [data-testid="stSidebar"] * { color: #E7EEF1; }
    [data-testid="stSidebar"] .sf-brand {
        display: flex; align-items: center; gap: 11px;
        padding: 4px 2px 14px 2px; margin-bottom: 6px;
        border-bottom: 1px solid rgba(255,255,255,.08);
    }
    [data-testid="stSidebar"] .sf-brand-mark {
        width: 38px; height: 38px; border-radius: 10px; flex: 0 0 auto;
        display: flex; align-items: center; justify-content: center; font-size: 20px;
        background: linear-gradient(135deg, var(--sf-blue), var(--sf-blue-deep));
        box-shadow: 0 4px 12px rgba(41,181,232,.35);
    }
    [data-testid="stSidebar"] .sf-brand-name { font-size: 1.02rem; font-weight: 800; color: #fff; line-height: 1.1; }
    [data-testid="stSidebar"] .sf-brand-tag { font-size: .72rem; color: #8FB6C6; font-weight: 500; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        text-transform: uppercase; letter-spacing: .08em; font-size: .7rem;
        font-weight: 700; color: #7FA3B3 !important;
    }
    /* Radio nav items as pills */
    [data-testid="stSidebar"] [role="radiogroup"] label {
        background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.06);
        border-radius: 10px; padding: 9px 12px; margin-bottom: 7px;
        transition: all .15s ease; cursor: pointer;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(41,181,232,.12); border-color: rgba(41,181,232,.4);
    }
    [data-testid="stSidebar"] .sf-status-card {
        margin-top: 10px; padding: 12px 14px; border-radius: 12px;
        background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.08);
    }
    [data-testid="stSidebar"] .sf-status-row { display: flex; justify-content: space-between; align-items: center; font-size: .82rem; margin: 3px 0; }
    [data-testid="stSidebar"] .sf-status-key { color: #8FB6C6; }
    [data-testid="stSidebar"] .sf-status-val { color: #fff; font-weight: 600; font-family: 'Inter', monospace; }
    [data-testid="stSidebar"] .sf-online { color: #35E08F; font-weight: 700; }

    /* ---- Buttons ---- */
    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
        border-radius: 10px; font-weight: 600; font-size: .9rem;
        border: 1px solid var(--sf-line); background: var(--sf-surface); color: var(--sf-navy);
        padding: 8px 16px; transition: all .15s ease; box-shadow: var(--sf-shadow);
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        border-color: var(--sf-blue); color: var(--sf-blue-deep);
        transform: translateY(-1px);
    }
    /* Primary submit (first form button = Send) */
    .stFormSubmitButton > button[kind="primaryFormSubmit"],
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--sf-blue), var(--sf-blue-deep));
        color: #fff; border: none;
    }

    /* ---- Inputs / selects / multiselect ---- */
    [data-baseweb="select"] > div, .stTextArea textarea, .stTextInput input {
        border-radius: 10px !important; border-color: var(--sf-line) !important;
        background: var(--sf-surface) !important;
    }
    [data-baseweb="tag"] { background: var(--sf-blue-deep) !important; border-radius: 8px !important; }

    /* ---- DataFrame ---- */
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        border-radius: var(--sf-radius); border: 1px solid var(--sf-line);
        box-shadow: var(--sf-shadow); overflow: hidden;
    }

    /* ---- Alerts (info / warning / error / success) ---- */
    [data-testid="stAlert"] { border-radius: 12px; border: 1px solid var(--sf-line); box-shadow: var(--sf-shadow); }

    /* ---- Dividers ---- */
    hr { border-color: var(--sf-line); }

    /* ---- Chat bubbles ---- */
    .sf-chat-wrap { display: flex; margin: 10px 0; }
    .sf-chat-user { justify-content: flex-end; }
    .sf-chat-ai { justify-content: flex-start; }
    .sf-bubble {
        max-width: 78%; padding: 12px 16px; border-radius: 16px;
        font-size: .93rem; line-height: 1.5; box-shadow: var(--sf-shadow);
    }
    .sf-bubble-user { background: linear-gradient(135deg, var(--sf-blue), var(--sf-blue-deep)); color: #fff; border-bottom-right-radius: 5px; }
    .sf-bubble-ai { background: var(--sf-surface); border: 1px solid var(--sf-line); color: var(--sf-ink); border-bottom-left-radius: 5px; }
    .sf-chat-role { font-size: .68rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; opacity: .7; margin-bottom: 3px; display: block; }

    /* ---- Info cards / detail rows ---- */
    .sf-card {
        background: var(--sf-surface); border: 1px solid var(--sf-line);
        border-radius: var(--sf-radius); padding: 18px 20px; box-shadow: var(--sf-shadow);
        margin-bottom: 4px;
    }
    .sf-kv { display: flex; justify-content: space-between; gap: 14px; padding: 7px 0; border-bottom: 1px dashed var(--sf-line); }
    .sf-kv:last-child { border-bottom: none; }
    .sf-kv-key { color: var(--sf-slate); font-size: .82rem; font-weight: 600; }
    .sf-kv-val { color: var(--sf-ink); font-size: .9rem; font-weight: 600; text-align: right; word-break: break-all; }
    .sf-mono { font-family: 'SFMono-Regular', ui-monospace, Menlo, monospace; font-size: .84rem; }

    /* ---- Badges ---- */
    .sf-badge {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 3px 11px; border-radius: 999px; font-size: .74rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: .04em;
    }
    .sf-badge-critical { background: #FDECEA; color: #B42318; border: 1px solid #F4B9B2; }
    .sf-badge-high     { background: #FFF3E5; color: #B25A00; border: 1px solid #F5CE9B; }
    .sf-badge-medium   { background: #FFF9E6; color: #9A7400; border: 1px solid #F0DE9B; }
    .sf-badge-low      { background: #E9F7F1; color: #0E6B4E; border: 1px solid #A9E0CB; }
    .sf-badge-neutral  { background: #EEF3F6; color: #445862; border: 1px solid #D3DEE4; }
    .sf-badge-fired    { background: #FDECEA; color: #B42318; border: 1px solid #F4B9B2; }
    .sf-badge-clear    { background: #E9F7F1; color: #0E6B4E; border: 1px solid #A9E0CB; }

    /* ---- Signal chips grid ---- */
    .sf-signal-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 4px; }
    .sf-signal {
        background: var(--sf-surface); border: 1px solid var(--sf-line);
        border-radius: 12px; padding: 12px 14px; box-shadow: var(--sf-shadow);
    }
    .sf-signal-on { border-color: #F4B9B2; background: linear-gradient(180deg,#FFF7F6,#FFFFFF); }
    .sf-signal-name { font-size: .78rem; font-weight: 700; color: var(--sf-ink); margin-bottom: 8px; }

    /* ---- Report preview terminal ---- */
    .stTextArea textarea[disabled] {
        font-family: 'SFMono-Regular', ui-monospace, Menlo, monospace !important;
        font-size: .82rem !important; line-height: 1.5 !important;
        background: #0F1E24 !important; color: #C7E7F2 !important;
        border-radius: 12px !important; -webkit-text-fill-color: #C7E7F2 !important;
    }

    /* ---- Modern data table (Command Center) ---- */
    .sf-table-wrap {
        background: var(--sf-surface); border: 1px solid var(--sf-line);
        border-radius: var(--sf-radius); box-shadow: var(--sf-shadow);
        overflow: hidden; margin-top: 6px;
    }
    .sf-table-scroll { max-height: 560px; overflow-y: auto; }
    table.sf-table { width: 100%; border-collapse: collapse; font-size: .86rem; }
    table.sf-table thead th {
        position: sticky; top: 0; z-index: 2;
        background: #F0F5F8; color: var(--sf-slate);
        text-align: left; font-weight: 700; font-size: .72rem;
        text-transform: uppercase; letter-spacing: .05em;
        padding: 13px 16px; border-bottom: 1px solid var(--sf-line); white-space: nowrap;
    }
    table.sf-table tbody td { padding: 12px 16px; border-bottom: 1px solid #EEF2F5; color: var(--sf-ink); vertical-align: middle; }
    table.sf-table tbody tr:last-child td { border-bottom: none; }
    table.sf-table tbody tr { transition: background .12s ease; }
    table.sf-table tbody tr:hover { background: #F6FAFC; }
    .sf-td-mono { font-family: 'SFMono-Regular', ui-monospace, Menlo, monospace; font-size: .8rem; color: var(--sf-navy); font-weight: 600; }
    .sf-td-sub { color: var(--sf-slate); font-size: .78rem; }
    /* score bar inside table */
    .sf-score { display: flex; align-items: center; gap: 8px; min-width: 120px; }
    .sf-score-track { flex: 1; height: 7px; border-radius: 5px; background: #E7EDF1; overflow: hidden; }
    .sf-score-fill { height: 100%; border-radius: 5px; }
    .sf-score-num { font-weight: 700; font-size: .82rem; color: var(--sf-navy); width: 26px; text-align: right; }
    /* status pill */
    .sf-status-pill {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 3px 10px; border-radius: 999px; font-size: .72rem; font-weight: 700; white-space: nowrap;
        background: #EEF3F6; color: #445862; border: 1px solid #D7E1E7;
    }
    .sf-status-pill .d { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
    .sf-status-open { color: #0E6B4E; background: #E9F7F1; border-color: #A9E0CB; }
    .sf-status-escalated { color: #B42318; background: #FDECEA; border-color: #F4B9B2; }
    .sf-status-review { color: #9A7400; background: #FFF9E6; border-color: #F0DE9B; }
    .sf-resp-reject { color: #B42318; font-weight: 700; }
    .sf-resp-none { color: #92A3AB; }

    /* ---- Case Investigator stat cards ---- */
    .sf-stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 6px; }
    .sf-stat {
        background: var(--sf-surface); border: 1px solid var(--sf-line); border-radius: var(--sf-radius);
        padding: 14px 16px; box-shadow: var(--sf-shadow); position: relative; overflow: hidden;
    }
    .sf-stat::before { content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background: linear-gradient(180deg,var(--sf-blue),var(--sf-blue-deep)); }
    .sf-stat-label { font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--sf-slate); margin-bottom: 7px; }
    .sf-stat-val { font-size: 1.15rem; font-weight: 800; color: var(--sf-navy); line-height: 1.2; word-break: break-word; }

    /* ---- Verification panel ---- */
    .sf-verify-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 8px; }
    .sf-verify-tile {
        background: var(--sf-surface); border: 1px solid var(--sf-line); border-radius: 12px;
        padding: 13px 15px; box-shadow: var(--sf-shadow);
    }
    .sf-verify-label { font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--sf-slate); margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
    .sf-verify-val { font-size: .95rem; font-weight: 700; color: var(--sf-navy); word-break: break-word; line-height: 1.35; }
    .sf-verify-val.mono { font-family: 'SFMono-Regular', ui-monospace, Menlo, monospace; font-size: .84rem; }
    .sf-deliv { display: inline-flex; gap: 6px; flex-wrap: wrap; }
    .sf-chiplet { display:inline-flex; align-items:center; gap:5px; padding:2px 9px; border-radius:999px; font-size:.74rem; font-weight:700; background:#E9F7F1; color:#0E6B4E; border:1px solid #A9E0CB; }
    .sf-chiplet.bad { background:#FDECEA; color:#B42318; border-color:#F4B9B2; }
    .sf-chiplet.muted { background:#EEF3F6; color:#5B6B73; border-color:#D7E1E7; }

    /* ---- CoCo chat interface ---- */
    .sf-chat-panel {
        background: linear-gradient(180deg,#FBFDFE 0%, #F4F8FA 100%);
        border: 1px solid var(--sf-line); border-radius: 16px;
        padding: 18px 18px 6px 18px; box-shadow: var(--sf-shadow);
        min-height: 220px; margin-bottom: 14px;
    }
    .sf-chat-row { display: flex; align-items: flex-end; gap: 10px; margin: 14px 0; }
    .sf-chat-row.user { flex-direction: row-reverse; }
    .sf-avatar {
        width: 34px; height: 34px; border-radius: 10px; flex: 0 0 auto;
        display: flex; align-items: center; justify-content: center; font-size: 18px;
        box-shadow: var(--sf-shadow);
    }
    .sf-avatar-ai { background: linear-gradient(135deg,var(--sf-blue),var(--sf-blue-deep)); color:#fff; }
    .sf-avatar-user { background: #E3EDF2; color: var(--sf-navy); border: 1px solid var(--sf-line); }
    .sf-bubble2 { max-width: 74%; padding: 11px 15px; border-radius: 16px; font-size: .93rem; line-height: 1.55; box-shadow: var(--sf-shadow); }
    .sf-bubble2.ai { background:#fff; border:1px solid var(--sf-line); color:var(--sf-ink); border-bottom-left-radius:5px; }
    .sf-bubble2.user { background: linear-gradient(135deg,var(--sf-blue),var(--sf-blue-deep)); color:#fff; border-bottom-right-radius:5px; }
    .sf-bubble2 .nm { font-size:.66rem; font-weight:700; text-transform:uppercase; letter-spacing:.06em; opacity:.65; display:block; margin-bottom:3px; }
    .sf-chat-empty { text-align:center; color:var(--sf-slate); padding: 26px 10px 14px 10px; }
    .sf-chat-empty .big { font-size: 34px; margin-bottom: 6px; }
    .sf-chat-empty .t1 { font-size: 1.05rem; font-weight: 800; color: var(--sf-navy); }
    .sf-chat-empty .t2 { font-size: .88rem; margin-top: 3px; }
    .sf-suggest-label { font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:var(--sf-slate); margin:2px 0 8px 2px; }

    /* Style the quick-action buttons as suggestion chips */
    .sf-suggest-zone .stButton > button {
        width: 100%; text-align: left; border-radius: 999px;
        background: #fff; border: 1px solid #CFE6F2; color: var(--sf-blue-deep);
        font-weight: 600; font-size: .86rem; padding: 9px 16px; box-shadow: none;
        white-space: normal; line-height: 1.3;
    }
    .sf-suggest-zone .stButton > button:hover {
        background: #EAF7FD; border-color: var(--sf-blue); transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(41,181,232,.18);
    }

    /* ---- Selectbox / dropdown: never trim option text ---- */
    [data-baseweb="select"] div[title] { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
    [data-baseweb="popover"] li, [data-baseweb="menu"] li, [role="option"] {
        white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
        height: auto !important; line-height: 1.35 !important; padding-top: 8px !important; padding-bottom: 8px !important;
    }
    [data-baseweb="select"] [data-baseweb="tag"] { white-space: normal !important; }

    /* ---- Markdown rendered inside chat bubbles ---- */
    .sf-bubble2 .sf-md-p { margin: 0 0 8px 0; }
    .sf-bubble2 .sf-md-p:last-child { margin-bottom: 0; }
    .sf-bubble2 .sf-md-h { font-weight: 800; color: var(--sf-navy); margin: 10px 0 6px 0; line-height: 1.25; }
    .sf-bubble2.user .sf-md-h { color: #EAF7FD; }
    .sf-bubble2 .sf-md-h1 { font-size: 1.12rem; }
    .sf-bubble2 .sf-md-h2 { font-size: 1.04rem; }
    .sf-bubble2 .sf-md-h3 { font-size: .98rem; }
    .sf-bubble2 .sf-md-h4, .sf-bubble2 .sf-md-h5, .sf-bubble2 .sf-md-h6 { font-size: .92rem; }
    .sf-bubble2 .sf-md-ul, .sf-bubble2 .sf-md-ol { margin: 4px 0 8px 0; padding-left: 20px; }
    .sf-bubble2 .sf-md-ul li, .sf-bubble2 .sf-md-ol li { margin: 3px 0; }
    .sf-bubble2 code {
        font-family: 'SFMono-Regular', ui-monospace, Menlo, monospace; font-size: .84em;
        background: rgba(16,36,43,.08); padding: 1px 5px; border-radius: 5px;
    }
    .sf-bubble2.user code { background: rgba(255,255,255,.22); }
    .sf-bubble2 .sf-md-pre {
        background: #0F1E24; color: #C7E7F2; border-radius: 10px; padding: 12px 14px;
        overflow-x: auto; margin: 8px 0; font-size: .82rem; line-height: 1.5;
    }
    .sf-bubble2 .sf-md-pre code { background: transparent; padding: 0; color: inherit; }
    .sf-bubble2 blockquote.sf-md-q {
        margin: 8px 0; padding: 6px 12px; border-left: 3px solid var(--sf-blue);
        background: rgba(41,181,232,.08); border-radius: 6px; color: inherit;
    }
    .sf-bubble2 .sf-md-hr { border: none; border-top: 1px solid var(--sf-line); margin: 10px 0; }
    .sf-bubble2 .sf-md-tablewrap { overflow-x: auto; margin: 8px 0; border-radius: 10px; }
    .sf-bubble2 table.sf-md-table { border-collapse: collapse; width: 100%; font-size: .84rem; background: #fff; }
    .sf-bubble2 table.sf-md-table th {
        background: #F0F5F8; color: var(--sf-slate); text-align: left; font-weight: 700;
        font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; padding: 8px 11px;
        border-bottom: 1px solid var(--sf-line); white-space: nowrap;
    }
    .sf-bubble2 table.sf-md-table td { padding: 8px 11px; border-bottom: 1px solid #EEF2F5; color: var(--sf-ink); }
    .sf-bubble2 table.sf-md-table tr:last-child td { border-bottom: none; }
    .sf-bubble2 a { color: var(--sf-blue-deep); font-weight: 600; }
    .sf-bubble2.user a { color: #EAF7FD; }

    /* ---- Native st.chat_input styled to match theme ---- */
    [data-testid="stChatInput"] { border-radius: 14px; border: 1px solid #CFE0E9; box-shadow: var(--sf-shadow); }
    [data-testid="stChatInput"] textarea { font-size: .95rem; }

    /* ---- Data-URI download buttons (anchor styled as button) ---- */
    .sf-dl-row { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 6px; }
    .sf-dl {
        flex: 1 1 200px; display: inline-flex; align-items: center; justify-content: center; gap: 8px;
        text-decoration: none; font-weight: 700; font-size: .92rem; padding: 11px 18px;
        border-radius: 10px; border: 1px solid var(--sf-line); background: var(--sf-surface);
        color: var(--sf-navy) !important; box-shadow: var(--sf-shadow); transition: all .15s ease;
        cursor: pointer;
    }
    .sf-dl:hover { border-color: var(--sf-blue); transform: translateY(-1px); box-shadow: 0 6px 16px rgba(41,181,232,.18); }
    .sf-dl-primary {
        background: linear-gradient(135deg, var(--sf-blue), var(--sf-blue-deep));
        color: #fff !important; border: none;
    }
    .sf-dl-primary:hover { filter: brightness(1.04); }

    /* ---- Responsiveness ---- */
    @media (max-width: 900px) {
        .block-container { padding-left: .8rem; padding-right: .8rem; }
        .sf-hero { padding: 20px 18px; }
        .sf-hero-title { font-size: 1.25rem; }
        .sf-hero-pills { display: none; }
        .sf-bubble2, .sf-bubble { max-width: 90% !important; }
        [data-testid="stMetricValue"] { font-size: 1.25rem !important; }
    }
    @media (max-width: 640px) {
        .sf-hero-row { flex-wrap: wrap; }
        .sf-stat-grid, .sf-verify-grid, .sf-signal-grid { grid-template-columns: 1fr 1fr; }
        .sf-dl { flex: 1 1 100%; }
    }

    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ---- Hero header -------------------------------------------------------------
st.markdown("""
<div class="sf-hero">
  <div class="sf-hero-row">
    <div class="sf-hero-mark">&#10052;&#65039;</div>
    <div>
      <p class="sf-hero-title">FraudShield&nbsp;360 &nbsp;&middot;&nbsp; Command Center</p>
      <p class="sf-hero-sub">Intelligent Fraud Detection &amp; Response Platform</p>
    </div>
    <div class="sf-hero-pills">
      <span class="sf-pill"><span class="sf-dot"></span> Live</span>
      <span class="sf-pill">Powered by Snowflake Cortex</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---- Logged-in user & role badge in header ----
_user_df = session.sql("SELECT CURRENT_USER() AS U").to_pandas()
_current_user_display = _user_df.iloc[0]["U"] if not _user_df.empty else "Unknown"
_role_display = " | ".join(ROLES) if ROLES else "No Role"
_role_label_map = {
    "FRAUDSHIELD_ACCESS_ADMIN_ROLE": "Account Admin",
    "COMPLIANCE_OFFICER_ROLE": "Compliance Officer",
    "FRAUD_ANALYST_ROLE": "Fraud Analyst",
    "AUDIT_ROLE": "Auditor",
}
_friendly_roles = [_role_label_map.get(r, r) for r in ROLES]
_friendly_display = " | ".join(_friendly_roles)

st.markdown(
    f'<div style="display:flex;align-items:center;justify-content:flex-end;padding:0.3rem 0.5rem;'
    f'margin-top:-0.5rem;margin-bottom:0.8rem;">'
    f'<span style="font-size:0.82rem;color:#5B6B73;margin-right:0.5rem;">'
    f'Logged in as</span>'
    f'<span style="font-size:0.85rem;font-weight:600;color:#16242B;margin-right:0.6rem;">'
    f'{_html.escape(_current_user_display)}</span>'
    f'<span style="background:#11567F;color:#fff;padding:3px 10px;border-radius:12px;'
    f'font-size:0.75rem;font-weight:600;letter-spacing:0.3px;">'
    f'{_html.escape(_friendly_display)}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ---- Sidebar branding & navigation ------------------------------------------
st.sidebar.markdown("""
<div class="sf-brand">
  <div class="sf-brand-mark">&#128737;&#65039;</div>
  <div>
    <div class="sf-brand-name">FraudShield&nbsp;360</div>
    <div class="sf-brand-tag">Sentinel AI Platform</div>
  </div>
</div>
""", unsafe_allow_html=True)

screen = st.sidebar.radio("Navigation", [
    "Command Center",
    "Case Investigator",
    "CoCo Chat",
    "Report Preview",
    "Metrics Dashboard",
    "Audit Log",
    "Access Management"
])

# Gate: Access Management only visible to FRAUDSHIELD_ACCESS_ADMIN_ROLE
if screen == "Access Management" and not require("FRAUDSHIELD_ACCESS_ADMIN_ROLE"):
    st.error("Access denied. The Access Management screen requires FRAUDSHIELD_ACCESS_ADMIN_ROLE.")
    st.stop()
# Gate: Audit Log only for AUDIT_ROLE or COMPLIANCE_OFFICER_ROLE
if screen == "Audit Log" and not (require("AUDIT_ROLE") or require("COMPLIANCE_OFFICER_ROLE")):
    st.error("Access denied. The Audit Log requires AUDIT_ROLE or COMPLIANCE_OFFICER_ROLE.")
    st.stop()
st.sidebar.divider()
st.sidebar.markdown("""
<div class="sf-status-card">
  <div class="sf-status-row"><span class="sf-status-key">Agent</span><span class="sf-status-val">SENTINEL_AI_ENGINE</span></div>
  <div class="sf-status-row"><span class="sf-status-key">Status</span><span class="sf-online">&#9679; Online</span></div>
  <div class="sf-status-row"><span class="sf-status-key">Engine</span><span class="sf-status-val">Cortex&nbsp;AI</span></div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# HELPERS
# =============================================================================
def safe_ts(val):
    """Return a clean timestamp string or 'Pending' for null/NaT."""
    if val is None or pd.isna(val):
        return "Pending"
    return str(val)[:19]


def safe_val(val, default="N/A"):
    """Return value or default if null/NaT/None."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return val


# ---- Presentational-only UI helpers (no data/logic changes) -----------------
def risk_badge(tier):
    """Return an HTML risk-tier badge string."""
    t = str(tier).upper().strip()
    cls = {
        "CRITICAL": "sf-badge-critical",
        "HIGH": "sf-badge-high",
        "MEDIUM": "sf-badge-medium",
        "LOW": "sf-badge-low",
    }.get(t, "sf-badge-neutral")
    return f'<span class="sf-badge {cls}">{t}</span>'


def kv_row(key, val, mono=False):
    """Return an HTML key/value detail row."""
    cls = "sf-kv-val sf-mono" if mono else "sf-kv-val"
    return f'<div class="sf-kv"><span class="sf-kv-key">{key}</span><span class="{cls}">{val}</span></div>'


def _esc(v):
    """HTML-escape any value for safe inline rendering."""
    return _html.escape("" if v is None else str(v))


def score_bar(score):
    """Return an HTML risk-score bar. Color scales with severity."""
    try:
        s = int(round(float(score)))
    except (ValueError, TypeError):
        s = 0
    s = max(0, min(100, s))
    if s >= 80:
        color = "#D92D20"
    elif s >= 60:
        color = "#E86E00"
    elif s >= 40:
        color = "#C9A100"
    else:
        color = "#17916B"
    return (
        f'<div class="sf-score"><div class="sf-score-track">'
        f'<div class="sf-score-fill" style="width:{s}%;background:{color};"></div></div>'
        f'<span class="sf-score-num">{s}</span></div>'
    )


def status_pill(status):
    """Return an HTML case-status pill."""
    s = str(status).upper().strip()
    cls = {
        "OPEN": "sf-status-open",
        "ESCALATED": "sf-status-escalated",
        "UNDER_REVIEW": "sf-status-review",
    }.get(s, "")
    label = s.replace("_", " ").title()
    return f'<span class="sf-status-pill {cls}"><span class="d"></span>{_esc(label)}</span>'


def response_cell(resp):
    """Return styled customer-response text for the alert table."""
    r = str(resp).upper().strip()
    if r == "USER_REJECTED":
        return f'<span class="sf-resp-reject">&#9888;&#65039; {_esc(r.replace("_", " ").title())}</span>'
    if r in ("NO_VERIFICATION", "NONE", "N/A"):
        return f'<span class="sf-resp-none">&mdash;</span>'
    return _esc(r.replace("_", " ").title())


def _md_inline(s):
    """Render inline markdown (bold, italic, code, links) after HTML-escaping."""
    s = _html.escape(s)
    s = _re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = _re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = _re.sub(r'__([^_]+)__', r'<strong>\1</strong>', s)
    s = _re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', s)
    # Underscore italics, but only when not inside_an_identifier (word chars on both outer sides fail)
    s = _re.sub(r'(?<![\w*])_([^_\n]+)_(?![\w*])', r'<em>\1</em>', s)
    s = _re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)',
                r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


def md_to_html(text):
    """Convert a subset of GitHub-flavored Markdown to safe HTML for chat bubbles.
    Supports headings, bold/italic/code, links, ordered/unordered lists, blockquotes,
    fenced code blocks, horizontal rules, and pipe tables."""
    lines = str(text).replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lines)

    def is_table_sep(line):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        return len(cells) >= 1 and all(_re.match(r'^:?-{1,}:?$', c) for c in cells if c != "") and any(cells)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Fenced code block
        if stripped.startswith("```"):
            code, i = [], i + 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(_html.escape(lines[i]))
                i += 1
            i += 1
            out.append('<pre class="sf-md-pre"><code>' + "\n".join(code) + "</code></pre>")
            continue

        # Pipe table
        if "|" in line and i + 1 < n and is_table_sep(lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            body = []
            while i < n and "|" in lines[i] and lines[i].strip():
                body.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join(f"<th>{_md_inline(h)}</th>" for h in header)
            trs = ""
            for row in body:
                row = (row + [""] * len(header))[:len(header)]
                trs += "<tr>" + "".join(f"<td>{_md_inline(c)}</td>" for c in row) + "</tr>"
            out.append(f'<div class="sf-md-tablewrap"><table class="sf-md-table">'
                       f'<thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')
            continue

        # Headings
        m = _re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            lvl = min(len(m.group(1)), 6)
            out.append(f'<div class="sf-md-h sf-md-h{lvl}">{_md_inline(m.group(2))}</div>')
            i += 1
            continue

        # Horizontal rule
        if _re.match(r'^(\-{3,}|\*{3,}|_{3,})$', stripped):
            out.append('<hr class="sf-md-hr">')
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(_md_inline(lines[i].strip()[1:].strip()))
                i += 1
            out.append('<blockquote class="sf-md-q">' + "<br>".join(quote) + "</blockquote>")
            continue

        # Unordered list
        if _re.match(r'^\s*[-*+]\s+', line):
            items = []
            while i < n and _re.match(r'^\s*[-*+]\s+', lines[i]):
                items.append("<li>" + _md_inline(_re.sub(r'^\s*[-*+]\s+', '', lines[i])) + "</li>")
                i += 1
            out.append('<ul class="sf-md-ul">' + "".join(items) + "</ul>")
            continue

        # Ordered list
        if _re.match(r'^\s*\d+\.\s+', line):
            items = []
            while i < n and _re.match(r'^\s*\d+\.\s+', lines[i]):
                items.append("<li>" + _md_inline(_re.sub(r'^\s*\d+\.\s+', '', lines[i])) + "</li>")
                i += 1
            out.append('<ol class="sf-md-ol">' + "".join(items) + "</ol>")
            continue

        # Blank line
        if stripped == "":
            i += 1
            continue

        # Paragraph (accumulate consecutive plain lines)
        para = [_md_inline(line)]
        i += 1
        while i < n and lines[i].strip() != "" and \
                not _re.match(r'^(#{1,6}\s|\s*[-*+]\s|\s*\d+\.\s|>|```)', lines[i]) and \
                "|" not in lines[i]:
            para.append(_md_inline(lines[i]))
            i += 1
        out.append('<p class="sf-md-p">' + "<br>".join(para) + "</p>")

    return "".join(out)


def download_link(label, data_bytes, filename, mime, primary=False):
    """Return an HTML anchor that downloads data via a base64 data URI.
    This bypasses Streamlit's presigned-URL media manager, which avoids the
    'SignatureDoesNotMatch' error that st.download_button can raise in
    Streamlit-in-Snowflake when a rerun invalidates the media file."""
    b64 = _base64.b64encode(data_bytes).decode("ascii")
    cls = "sf-dl sf-dl-primary" if primary else "sf-dl"
    return (f'<a class="{cls}" download="{_esc(filename)}" '
            f'href="data:{mime};base64,{b64}">{label}</a>')


def build_sar_pdf(report_text, case_id):
    """Render the plain-text SAR report into a professional PDF (bytes).
    Uses reportlab if available in the SiS environment; returns None if it is not,
    so the caller can fall back to a text download."""
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        from reportlab.pdfgen import canvas as _canvas
    except Exception:
        return None

    try:
        buf = BytesIO()
        c = _canvas.Canvas(buf, pagesize=LETTER)
        width, height = LETTER
        margin_x = 0.85 * inch
        top = height - 0.9 * inch
        line_h = 12.5

        def header_band():
            c.setFillColor(HexColor("#11567F"))
            c.rect(0, height - 0.7 * inch, width, 0.7 * inch, fill=1, stroke=0)
            c.setFillColor(HexColor("#FFFFFF"))
            c.setFont("Helvetica-Bold", 13)
            c.drawString(margin_x, height - 0.47 * inch, "FraudShield 360  \u2014  Suspicious Activity Report")
            c.setFont("Helvetica", 8)
            c.drawRightString(width - margin_x, height - 0.47 * inch, "CONFIDENTIAL \u2022 DRAFT")

        def footer_band(page_no):
            c.setFillColor(HexColor("#8A9AA3"))
            c.setFont("Helvetica", 7.5)
            c.drawString(margin_x, 0.55 * inch,
                         "Generated by FraudShield 360 \u2022 Not reviewed or filed \u2022 Do not distribute")
            c.drawRightString(width - margin_x, 0.55 * inch, f"Page {page_no}")

        header_band()
        page_no = 1
        footer_band(page_no)
        y = top - 0.35 * inch
        c.setFillColor(HexColor("#16242B"))

        for raw_line in report_text.split("\n"):
            line = raw_line.replace("\t", "    ")
            # section headers get emphasis
            is_section = line.strip().startswith("SECTION") or line.strip().startswith("===")
            if line.strip().startswith("\u2501") or set(line.strip()) == {"\u2501"}:
                # divider rule
                c.setStrokeColor(HexColor("#D6DEE3"))
                c.setLineWidth(0.6)
                c.line(margin_x, y + 3, width - margin_x, y + 3)
                y -= line_h
            else:
                if is_section:
                    c.setFont("Helvetica-Bold", 9.5)
                    c.setFillColor(HexColor("#11567F"))
                else:
                    c.setFont("Helvetica", 8.8)
                    c.setFillColor(HexColor("#16242B"))
                # wrap long lines
                max_chars = 100
                chunk = line if len(line) <= max_chars else line[:max_chars]
                c.drawString(margin_x, y, chunk)
                if len(line) > max_chars:
                    y -= line_h
                    c.drawString(margin_x + 0.2 * inch, y, line[max_chars:200])
                y -= line_h

            if y < 0.9 * inch:
                footer_band(page_no)
                c.showPage()
                page_no += 1
                header_band()
                footer_band(page_no)
                y = top - 0.35 * inch

        c.showPage()
        c.save()
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None


# =============================================================================
# SCREEN 1: COMMAND CENTER
# =============================================================================
if screen == "Command Center":
    st.header("Live Alert Feed")

    # Summary metrics
    summary = session.sql("""
        SELECT
            COUNT(*) AS total,
            COUNT(CASE WHEN RISK_TIER = 'CRITICAL' THEN 1 END) AS critical,
            COUNT(CASE WHEN RISK_TIER = 'HIGH' THEN 1 END) AS high,
            COUNT(CASE WHEN CASE_STATUS = 'OPEN' THEN 1 END) AS open_cases,
            COUNT(CASE WHEN CASE_STATUS = 'ESCALATED' THEN 1 END) AS escalated
        FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
    """).to_pandas().iloc[0]

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Alerts", int(summary["TOTAL"]))
    m2.metric("Critical", int(summary["CRITICAL"]))
    m3.metric("High Risk", int(summary["HIGH"]))
    m4.metric("Open Cases", int(summary["OPEN_CASES"]))
    m5.metric("Escalated", int(summary["ESCALATED"]))

    st.divider()

    # Filters
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        tier_filter = st.multiselect("Risk Tier", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=["CRITICAL", "HIGH", "MEDIUM", "LOW"])
    with fc2:
        status_options = ["OPEN", "UNDER_REVIEW", "ESCALATED", "RESOLVED_CONFIRMED"]
        status_filter = st.multiselect("Case Status", status_options, default=["OPEN", "UNDER_REVIEW", "ESCALATED"])
    with fc3:
        row_limit = st.selectbox("Max Rows", [25, 50, 100, 200], index=1)

    tier_in = ",".join([f"'{t}'" for t in tier_filter])
    status_in = ",".join([f"'{s}'" for s in status_filter])

    alerts_df = session.sql(f"""
        SELECT
            fa.CASE_ID,
            fa.ACCOUNT_ID,
            fa.ALERT_TYPE,
            fa.RISK_TIER,
            fa.RISK_SCORE,
            fa.CASE_STATUS,
            fa.ASSIGNED_ANALYST,
            TO_VARCHAR(fa.ALERT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') AS ALERT_TIME,
            COALESCE(cve.RESPONSE_TYPE, 'NO_VERIFICATION') AS CUSTOMER_RESPONSE
        FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS fa
        LEFT JOIN FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS cve
            ON fa.CASE_ID = cve.CASE_ID
        WHERE fa.RISK_TIER IN ({tier_in})
          AND fa.CASE_STATUS IN ({status_in})
        ORDER BY fa.ALERT_TIMESTAMP DESC
        LIMIT {row_limit}
    """).to_pandas()

    if alerts_df.empty:
        st.info("No alerts match the current filters.")
    else:
        st.caption(f"Showing {len(alerts_df)} alert(s), newest first.")
        try:
            rows_html = []
            for _, r in alerts_df.iterrows():
                analyst = safe_val(r.get("ASSIGNED_ANALYST"), "Unassigned")
                rows_html.append(
                    "<tr>"
                    f'<td><span class="sf-td-mono">{_esc(r.get("CASE_ID"))}</span></td>'
                    f'<td><span class="sf-td-mono">{_esc(r.get("ACCOUNT_ID"))}</span></td>'
                    f'<td>{_esc(r.get("ALERT_TYPE"))}</td>'
                    f'<td>{risk_badge(r.get("RISK_TIER"))}</td>'
                    f'<td>{score_bar(r.get("RISK_SCORE"))}</td>'
                    f'<td>{status_pill(r.get("CASE_STATUS"))}</td>'
                    f'<td>{_esc(analyst)}</td>'
                    f'<td><span class="sf-td-sub">{_esc(r.get("ALERT_TIME"))}</span></td>'
                    f'<td>{response_cell(r.get("CUSTOMER_RESPONSE"))}</td>'
                    "</tr>"
                )
            table_html = (
                '<div class="sf-table-wrap"><div class="sf-table-scroll">'
                '<table class="sf-table"><thead><tr>'
                "<th>Case ID</th><th>Account</th><th>Alert Type</th><th>Risk Tier</th>"
                "<th>Risk Score</th><th>Status</th><th>Analyst</th><th>Alert Time</th>"
                "<th>Customer Response</th>"
                "</tr></thead><tbody>"
                + "".join(rows_html) +
                "</tbody></table></div></div>"
            )
            st.markdown(table_html, unsafe_allow_html=True)
        except Exception:
            st.dataframe(alerts_df, use_container_width=True)


# =============================================================================
# SCREEN 2: CASE INVESTIGATOR
# =============================================================================
elif screen == "Case Investigator":
    st.header("Case Investigator")

    cases_df = session.sql("""
        SELECT CASE_ID, ACCOUNT_ID, RISK_TIER, ALERT_TYPE, RISK_SCORE, CASE_STATUS
        FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
        ORDER BY ALERT_TIMESTAMP DESC LIMIT 50
    """).to_pandas()

    if cases_df.empty:
        st.info("No cases available.")
    else:
        case_options = cases_df.apply(
            lambda r: f"{r['CASE_ID']}  \u2022  {r['RISK_TIER']}  \u2022  {r['ALERT_TYPE']}  \u2022  Score {r['RISK_SCORE']}", axis=1
        ).tolist()
        selected_idx = st.selectbox(
            "Select a case",
            range(len(case_options)),
            format_func=lambda i: case_options[i],
            help="Showing the 50 most recent cases (newest first).",
        )
        selected_case_id = cases_df.iloc[selected_idx]["CASE_ID"]

        st.divider()

        # Fetch joined data
        case_detail = session.sql("""
            SELECT fa.*, te.AMOUNT, te.MERCHANT, te.GEO_COUNTRY, te.GEO_CITY,
                   te.CHANNEL, te.TXN_TIMESTAMP, te.DEVICE_ID,
                   te.SIGNAL_VELOCITY, te.SIGNAL_AMOUNT_ANOMALY, te.SIGNAL_GEO_MISMATCH,
                   te.SIGNAL_WATCHLIST_MATCH, te.SIGNAL_STRUCTURING, te.SIGNAL_ROUND_NUMBER,
                   te.RISK_SCORE AS TXN_RISK_SCORE, te.RISK_TIER AS TXN_RISK_TIER
            FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS fa
            LEFT JOIN FRAUDSHIELD_360_DB.CURATED.TRANSACTION_ENRICHED te ON fa.TXN_ID = te.TXN_ID
            WHERE fa.CASE_ID = ?
        """, params=[selected_case_id]).to_pandas()

        verification_detail = session.sql("""
            SELECT * FROM FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS
            WHERE CASE_ID = ?
            ORDER BY ALERT_DISPATCHED_AT DESC LIMIT 1
        """, params=[selected_case_id]).to_pandas()

        if not case_detail.empty:
            # Log case-view audit event
            try:
                session.sql("""
                    INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                    (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                    VALUES (?, 'CASE_VIEWED', CURRENT_USER(), 'Case detail opened in investigator')
                """, params=[selected_case_id]).collect()
            except Exception:
                pass
            cd = case_detail.iloc[0]
            risk_score = safe_val(cd.get("TXN_RISK_SCORE", cd.get("RISK_SCORE", 0)), 0)
            risk_tier = safe_val(cd.get("TXN_RISK_TIER", cd.get("RISK_TIER", "N/A")))
            amount = cd.get("AMOUNT")
            amount_str = f"${amount:,.2f}" if pd.notna(amount) else "N/A"

            # Top-level case snapshot (custom cards so long values never trim)
            case_status_val = cd.get("CASE_STATUS", "N/A")
            st.markdown(
                '<div class="sf-stat-grid">'
                f'<div class="sf-stat"><div class="sf-stat-label">Risk Score</div>'
                f'<div class="sf-stat-val">{_esc(risk_score)}<span style="font-size:.8rem;color:#92A3AB;">/100</span></div></div>'
                f'<div class="sf-stat"><div class="sf-stat-label">Risk Tier</div>'
                f'<div class="sf-stat-val">{risk_badge(risk_tier)}</div></div>'
                f'<div class="sf-stat"><div class="sf-stat-label">Amount</div>'
                f'<div class="sf-stat-val">{_esc(amount_str)}</div></div>'
                f'<div class="sf-stat"><div class="sf-stat-label">Channel</div>'
                f'<div class="sf-stat-val">{_esc(safe_val(cd.get("CHANNEL")))}</div></div>'
                f'<div class="sf-stat"><div class="sf-stat-label">Case Status</div>'
                f'<div class="sf-stat-val">{status_pill(case_status_val)}</div></div>'
                '</div>',
                unsafe_allow_html=True,
            )

            # Transaction details
            st.subheader("Transaction Details")
            t1, t2 = st.columns(2)
            with t1:
                st.markdown(
                    '<div class="sf-card">'
                    + kv_row("TXN ID", _esc(safe_val(cd.get('TXN_ID'))), mono=True)
                    + kv_row("Merchant", _esc(safe_val(cd.get('MERCHANT'))))
                    + kv_row("Location", _esc(f"{safe_val(cd.get('GEO_CITY'))}, {safe_val(cd.get('GEO_COUNTRY'))}"))
                    + kv_row("Timestamp", _esc(safe_ts(cd.get('TXN_TIMESTAMP'))), mono=True)
                    + '</div>',
                    unsafe_allow_html=True,
                )
            with t2:
                st.markdown(
                    '<div class="sf-card">'
                    + kv_row("Account", _esc(cd.get('ACCOUNT_ID', 'N/A')), mono=True)
                    + kv_row("Device", _esc(safe_val(cd.get('DEVICE_ID'))), mono=True)
                    + kv_row("Analyst", _esc(safe_val(cd.get('ASSIGNED_ANALYST'), 'Unassigned')))
                    + kv_row("Alert Type", _esc(safe_val(cd.get('ALERT_TYPE'))))
                    + '</div>',
                    unsafe_allow_html=True,
                )

            # Signals
            st.subheader("Triggered Signals")
            signals = [
                ("Velocity", "15pt", "SIGNAL_VELOCITY"),
                ("Amount Anomaly", "25pt", "SIGNAL_AMOUNT_ANOMALY"),
                ("Geo Mismatch", "20pt", "SIGNAL_GEO_MISMATCH"),
                ("Watchlist", "30pt", "SIGNAL_WATCHLIST_MATCH"),
                ("Structuring", "20pt", "SIGNAL_STRUCTURING"),
                ("Round Number", "5pt", "SIGNAL_ROUND_NUMBER"),
            ]
            sig_html = ['<div class="sf-signal-grid">']
            for label, weight, col in signals:
                fired = bool(cd.get(col, False))
                on_cls = " sf-signal-on" if fired else ""
                badge = ('<span class="sf-badge sf-badge-fired">Fired</span>' if fired
                         else '<span class="sf-badge sf-badge-clear">Clear</span>')
                sig_html.append(
                    f'<div class="sf-signal{on_cls}">'
                    f'<div class="sf-signal-name">{label} &middot; {weight}</div>'
                    f'{badge}</div>'
                )
            sig_html.append('</div>')
            st.markdown("".join(sig_html), unsafe_allow_html=True)

            st.divider()

            # Verification Status Panel
            st.subheader("Verification Status Panel")

            if not verification_detail.empty:
                vd = verification_detail.iloc[0]
                response_type = safe_val(vd.get("RESPONSE_TYPE"), "N/A")

                # Compromise banner
                if response_type == "USER_REJECTED":
                    st.error("⚠️ ACCOUNT COMPROMISE SUSPECTED — Customer rejected this transaction. Immediate escalation required.")

                # Delivery status chiplets
                def _deliv_chip(channel, val):
                    v = str(safe_val(val, "—")).upper()
                    if v in ("SENT", "DELIVERED", "OPENED"):
                        cls = ""
                    elif v in ("FAILED", "BOUNCED", "UNDELIVERED"):
                        cls = " bad"
                    else:
                        cls = " muted"
                    return f'<span class="sf-chiplet{cls}">{_esc(channel)}: {_esc(val if val is not None else "—")}</span>'

                deliv_html = (
                    '<div class="sf-deliv">'
                    + _deliv_chip("Email", safe_val(vd.get("EMAIL_STATUS"), "—"))
                    + _deliv_chip("Push", safe_val(vd.get("PUSH_STATUS"), "—"))
                    + '</div>'
                )

                rt = str(response_type).upper()
                resp_cls = "bad" if rt == "USER_REJECTED" else ("" if rt in ("USER_CONFIRMED", "CONFIRMED") else "muted")
                resp_chip = f'<span class="sf-chiplet {resp_cls}">{_esc(str(response_type).replace("_", " ").title())}</span>'

                st.markdown(
                    '<div class="sf-verify-grid">'
                    f'<div class="sf-verify-tile"><div class="sf-verify-label">&#128228; Dispatch Time</div>'
                    f'<div class="sf-verify-val mono">{_esc(safe_ts(vd.get("ALERT_DISPATCHED_AT")))}</div></div>'
                    f'<div class="sf-verify-tile"><div class="sf-verify-label">&#128233; Delivery Status</div>'
                    f'<div class="sf-verify-val">{deliv_html}</div></div>'
                    f'<div class="sf-verify-tile"><div class="sf-verify-label">&#128100; Customer Response</div>'
                    f'<div class="sf-verify-val">{resp_chip}</div></div>'
                    f'<div class="sf-verify-tile"><div class="sf-verify-label">&#9201;&#65039; Response Time</div>'
                    f'<div class="sf-verify-val">{_esc(safe_val(vd.get("RESPONSE_TIME_MINUTES"), "Pending"))} min</div></div>'
                    f'<div class="sf-verify-tile"><div class="sf-verify-label">&#128273; Verification Method</div>'
                    f'<div class="sf-verify-val">{_esc(safe_val(vd.get("VERIFICATION_METHOD")))}</div></div>'
                    f'<div class="sf-verify-tile"><div class="sf-verify-label">&#128340; Response Timestamp</div>'
                    f'<div class="sf-verify-val mono">{_esc(safe_ts(vd.get("RESPONSE_TIMESTAMP")))}</div></div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

                explanation = vd.get("EXPLANATION_CUSTOMER")
                if explanation and pd.notna(explanation):
                    email_status = safe_val(vd.get("EMAIL_STATUS"), "UNKNOWN")
                    st.info(f"**Notification delivered** (Email: {email_status}): {explanation}")
            else:
                st.warning("No verification event dispatched for this case.")

            # =================================================================
            # CASE RESOLUTION PANEL — DATA-DRIVEN STATE MACHINE
            # =================================================================
            st.divider()
            st.subheader("Case Resolution Panel")

            current_status = cd.get("CASE_STATUS", "OPEN")
            current_version = cd.get("ROW_VERSION", 1) or 1
            case_risk_score = int(safe_val(cd.get("TXN_RISK_SCORE", cd.get("RISK_SCORE", 0)), 0))
            case_risk_tier = str(safe_val(cd.get("TXN_RISK_TIER", cd.get("RISK_TIER", ""))))

            TERMINAL_STATES = {"RESOLVED_APPROVED", "SAR_FILED", "CLOSED"}

            if current_status in TERMINAL_STATES or IS_READ_ONLY:
                # Locked summary
                st.info("**Case Resolved & Locked**" if current_status in TERMINAL_STATES
                        else "**Read-Only Access** — AUDIT_ROLE cannot perform actions.")
                resolution_info = session.sql("""
                    SELECT CASE_STATUS, RESOLVED_BY, RESOLVED_AT, RESOLUTION_NOTES
                    FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
                    WHERE CASE_ID = ?
                """, params=[selected_case_id]).to_pandas()
                if not resolution_info.empty:
                    ri = resolution_info.iloc[0]
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        st.markdown(f"**Final Status:** `{safe_val(ri.get('CASE_STATUS'))}`")
                        st.markdown(f"**Resolved By:** {safe_val(ri.get('RESOLVED_BY'), 'System')}")
                    with rc2:
                        st.markdown(f"**Resolved At:** {safe_ts(ri.get('RESOLVED_AT'))}")
                        st.markdown(f"**Notes:** {safe_val(ri.get('RESOLUTION_NOTES'), 'None')}")
            else:
                # Compute legal edges for this status + user roles
                all_edges = session.sql("""
                    SELECT FROM_STATUS, TO_STATUS, LABEL, REQUIRED_ROLE, REQUIRES_FOUR_EYES
                    FROM FRAUDSHIELD_360_DB.AGENTS.CASE_STATUS_TRANSITIONS
                    WHERE FROM_STATUS = ?
                """, params=[current_status]).to_pandas()

                legal_edges = all_edges[all_edges["REQUIRED_ROLE"].isin(ROLES)]

                if legal_edges.empty:
                    st.warning("No actions available for your role on this case status.")
                else:
                    st.markdown(f"**Current Status:** `{current_status}` &nbsp; | &nbsp; **Version:** {current_version}")

                    with st.form("case_state_machine_form"):
                        edge_labels = legal_edges["LABEL"].tolist()
                        selected_label = st.selectbox("Action", edge_labels)
                        compliance_notes = st.text_area("Notes", height=80, placeholder="Enter justification...")
                        action_submitted = st.form_submit_button("Execute Action")

                    if action_submitted:
                        edge_row = legal_edges[legal_edges["LABEL"] == selected_label].iloc[0]
                        to_status = edge_row["TO_STATUS"]
                        required_role = edge_row["REQUIRED_ROLE"]
                        four_eyes = bool(edge_row["REQUIRES_FOUR_EYES"])

                        try:
                            # (1) Edge verified above via query
                            # (2) Role verified via legal_edges filter

                            # (3) Four-eyes check
                            if four_eyes:
                                escalated_by_df = session.sql("""
                                    SELECT ESCALATED_BY FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
                                    WHERE CASE_ID = ?
                                """, params=[selected_case_id]).to_pandas()
                                esc_by = escalated_by_df.iloc[0]["ESCALATED_BY"] if not escalated_by_df.empty else None

                                current_user_df = session.sql("SELECT CURRENT_USER() AS U").to_pandas()
                                current_user = current_user_df.iloc[0]["U"]

                                if esc_by and current_user == esc_by:
                                    st.error("Four-eyes violation: you cannot approve a case you escalated.")
                                    st.stop()

                                # Additional check for PENDING_SAR -> SAR_FILED
                                if current_status == "PENDING_SAR" and to_status == "SAR_FILED":
                                    opened_by_df = session.sql("""
                                        SELECT OPENED_BY FROM FRAUDSHIELD_360_DB.AGENTS.SAR_FILINGS
                                        WHERE CASE_ID = ? AND STATUS = 'PENDING'
                                        ORDER BY OPENED_AT DESC LIMIT 1
                                    """, params=[selected_case_id]).to_pandas()
                                    if not opened_by_df.empty and opened_by_df.iloc[0]["OPENED_BY"] == current_user:
                                        st.error("Four-eyes violation: you cannot file a SAR you opened.")
                                        st.stop()

                            # (4) Analyst self-approval threshold
                            if to_status == "RESOLVED_APPROVED" and required_role == "FRAUD_ANALYST_ROLE":
                                config_df = session.sql("""
                                    SELECT CONFIG_KEY, CONFIG_VALUE FROM FRAUDSHIELD_360_DB.AGENTS.APP_CONFIG
                                    WHERE CONFIG_KEY IN ('ANALYST_MAX_RISK_SCORE', 'ANALYST_BLOCKED_TIERS')
                                """).to_pandas()
                                config = dict(zip(config_df["CONFIG_KEY"], config_df["CONFIG_VALUE"]))
                                max_score = int(config.get("ANALYST_MAX_RISK_SCORE", 60))
                                blocked_tiers = [t.strip() for t in config.get("ANALYST_BLOCKED_TIERS", "").split(",")]

                                if case_risk_score >= max_score:
                                    st.error(f"Cannot self-approve: risk score {case_risk_score} >= threshold {max_score}. Escalate instead.")
                                    st.stop()
                                if case_risk_tier in blocked_tiers:
                                    st.error(f"Cannot self-approve: risk tier '{case_risk_tier}' requires escalation.")
                                    st.stop()

                            # (5) Optimistic lock update
                            new_version = int(current_version) + 1
                            is_resolution = to_status in ("RESOLVED_APPROVED", "SAR_FILED", "CLOSED")

                            if is_resolution:
                                rows_updated = session.sql("""
                                    UPDATE FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
                                    SET CASE_STATUS = ?,
                                        RESOLVED_BY = CURRENT_USER(),
                                        RESOLVED_AT = CURRENT_TIMESTAMP(),
                                        RESOLUTION_NOTES = ?,
                                        ROW_VERSION = ?
                                    WHERE CASE_ID = ? AND ROW_VERSION = ?
                                """, params=[to_status, compliance_notes or '', new_version, selected_case_id, current_version]).collect()
                            elif to_status == "ESCALATED":
                                rows_updated = session.sql("""
                                    UPDATE FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
                                    SET CASE_STATUS = ?,
                                        ESCALATED_BY = CURRENT_USER(),
                                        ESCALATED_AT = CURRENT_TIMESTAMP(),
                                        ESCALATED_TO = 'COMPLIANCE_OFFICER_ROLE',
                                        SLA_DUE_AT = DATEADD(HOUR, 8, CURRENT_TIMESTAMP()),
                                        RESOLUTION_NOTES = ?,
                                        ROW_VERSION = ?
                                    WHERE CASE_ID = ? AND ROW_VERSION = ?
                                """, params=[to_status, compliance_notes or '', new_version, selected_case_id, current_version]).collect()
                            else:
                                rows_updated = session.sql("""
                                    UPDATE FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
                                    SET CASE_STATUS = ?,
                                        RESOLUTION_NOTES = ?,
                                        ROW_VERSION = ?
                                    WHERE CASE_ID = ? AND ROW_VERSION = ?
                                """, params=[to_status, compliance_notes or '', new_version, selected_case_id, current_version]).collect()

                            # Check optimistic lock
                            verify_df = session.sql("""
                                SELECT ROW_VERSION FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS WHERE CASE_ID = ?
                            """, params=[selected_case_id]).to_pandas()
                            actual_version = int(verify_df.iloc[0]["ROW_VERSION"]) if not verify_df.empty else 0
                            if actual_version != new_version:
                                st.error("Case changed by another user. Please refresh and try again.")
                                st.stop()

                            # (6) Audit row
                            session.sql("""
                                INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                                (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                                VALUES (?, ?, CURRENT_USER(), ?)
                            """, params=[selected_case_id, f"{current_status}->{to_status}", compliance_notes or '']).collect()

                            # Side-effects for Escalate
                            if to_status == "ESCALATED":
                                session.sql("""
                                    INSERT INTO FRAUDSHIELD_360_DB.AGENTS.CASE_WORKFLOW_QUEUE
                                    (CASE_ID, ASSIGNED_TO_ROLE, QUEUED_BY, SLA_DUE_AT)
                                    VALUES (?, 'COMPLIANCE_OFFICER_ROLE', CURRENT_USER(), DATEADD(HOUR, 8, CURRENT_TIMESTAMP()))
                                """, params=[selected_case_id]).collect()

                                # Send real escalation notification email
                                try:
                                    notif_msg = f"ESCALATION: Case {selected_case_id} escalated to COMPLIANCE_OFFICER_ROLE. SLA: 8 hours. Notes: {compliance_notes or 'None'}"
                                    session.sql("""
                                        CALL SYSTEM$SEND_EMAIL(
                                            'FRAUDSHIELD_EMAIL_INT',
                                            'owendrilasaha09@gmail.com',
                                            'FraudShield Alert: Case Escalated',
                                            ?
                                        )
                                    """, params=[notif_msg]).collect()
                                    session.sql("""
                                        INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                                        (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                                        VALUES (?, 'ESCALATION_EMAIL_SENT', CURRENT_USER(), 'Notification delivered via FRAUDSHIELD_EMAIL_INT')
                                    """, params=[selected_case_id]).collect()
                                except Exception as notif_err:
                                    print(f"[ESCALATION_NOTIF_ERROR] {notif_err}")
                                    session.sql("""
                                        INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                                        (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                                        VALUES (?, 'ESCALATION_EMAIL_FAILED', CURRENT_USER(), ?)
                                    """, params=[selected_case_id, str(notif_err)[:500]]).collect()

                            # Side-effects for Block & File SAR
                            if to_status == "PENDING_SAR":
                                account_id = cd.get("ACCOUNT_ID", "")
                                session.sql("""
                                    INSERT INTO FRAUDSHIELD_360_DB.AGENTS.SAR_FILINGS
                                    (CASE_ID, OPENED_BY, FILING_DEADLINE)
                                    VALUES (?, CURRENT_USER(), DATEADD(DAY, 30, CURRENT_TIMESTAMP()))
                                """, params=[selected_case_id]).collect()
                                session.sql("""
                                    INSERT INTO FRAUDSHIELD_360_DB.AGENTS.ACCOUNT_RISK_FLAGS
                                    (ACCOUNT_ID, FLAG_TYPE, EXPIRES_AT)
                                    VALUES (?, 'ENHANCED_MONITORING', DATEADD(HOUR, 72, CURRENT_TIMESTAMP()))
                                """, params=[account_id]).collect()

                            st.success(f"Case transitioned: **{current_status}** → **{to_status}**")
                            _rerun()

                        except Exception as e:
                            print(f"[STATE_MACHINE_ERROR] case={selected_case_id} edge={current_status}->{to_status} error={e}")
                            st.error("An error occurred during case transition. Please try again.")


# =============================================================================
# SCREEN 3: COCO CHAT
# =============================================================================
elif screen == "CoCo Chat":
    st.header("CoCo — Sentinel AI Assistant")
    st.caption("Your conversational fraud analyst. Ask about cases, risk signals, AML policy, or metrics.")

    # Chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    def coco_generate(user_text):
        """Append the user's message, query Sentinel AI via Cortex, append the reply."""
        user_text = user_text.strip()
        if not user_text:
            return
        st.session_state.chat_messages.append({"role": "user", "content": user_text})

        with st.spinner("CoCo is analyzing fraud signals..."):
            try:
                # Build context from recent alerts (no PII — only case/risk metadata)
                context_df = session.sql("""
                    SELECT TOP 5 CASE_ID, RISK_TIER, RISK_SCORE, ALERT_TYPE, CASE_STATUS
                    FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
                    ORDER BY ALERT_TIMESTAMP DESC
                """).to_pandas()
                context_str = context_df.to_string(index=False) if not context_df.empty else "No recent alerts."

                system_prompt = (
                    "You are Sentinel AI, the FraudShield 360 fraud detection assistant. "
                    "Answer questions about fraud alerts, transaction risk, AML compliance, and case investigations. "
                    "Be concise and precise. Do not include or request any PII. "
                    "Here is recent alert context:\n" + context_str
                )

                # Pass user input as bind parameter to CORTEX.COMPLETE
                result_df = session.sql("""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        'claude-haiku-4-5',
                        CONCAT(?, '\n\nUser question: ', ?, '\n\nAnswer:')
                    ) AS response
                """, params=[system_prompt, user_text]).to_pandas()

                if not result_df.empty and result_df["RESPONSE"].iloc[0]:
                    response_text = str(result_df["RESPONSE"].iloc[0]).strip()
                else:
                    response_text = "I could not generate a response. Please rephrase your question."

            except Exception as e:
                print(f"[COCO_CHAT_ERROR] {e}")
                response_text = "An error occurred while processing your request. Please try again."

        st.session_state.chat_messages.append({"role": "assistant", "content": response_text})

    # ---- Conversation panel (assistant markdown fully rendered) ----
    chat_html = ['<div class="sf-chat-panel">']
    if not st.session_state.chat_messages:
        chat_html.append(
            '<div class="sf-chat-empty">'
            '<div class="big">&#10052;&#65039;</div>'
            '<div class="t1">Hi, I\'m CoCo</div>'
            '<div class="t2">Ask me about fraud cases, risk signals, AML thresholds, or verification metrics.</div>'
            '</div>'
        )
    else:
        for msg in st.session_state.chat_messages:
            is_user = msg["role"] == "user"
            row_cls = "user" if is_user else "ai"
            av_cls = "sf-avatar-user" if is_user else "sf-avatar-ai"
            av_icon = "&#128100;" if is_user else "&#10052;&#65039;"
            bub_cls = "user" if is_user else "ai"
            role_name = "You" if is_user else "CoCo"
            # User text is shown verbatim (escaped); CoCo replies render markdown.
            if is_user:
                body = _html.escape(str(msg["content"])).replace("\n", "<br>")
            else:
                body = md_to_html(msg["content"])
            chat_html.append(
                f'<div class="sf-chat-row {row_cls}">'
                f'<div class="sf-avatar {av_cls}">{av_icon}</div>'
                f'<div class="sf-bubble2 {bub_cls}"><span class="nm">{role_name}</span>{body}</div>'
                f'</div>'
            )
    chat_html.append('</div>')
    st.markdown("".join(chat_html), unsafe_allow_html=True)

    # ---- Suggestion chips (trigger Sentinel AI engine on click) ----
    suggestions = [
        ("\U0001F6A8", "Recent high-risk alerts", "Show me the most recent critical and high-risk fraud alerts."),
        ("\U0001F4DC", "AML thresholds", "What are the AML transaction monitoring thresholds and reporting requirements?"),
        ("\U0001F4CA", "Verification stats", "What is the current verification acceptance rate and average response time?"),
    ]
    st.markdown('<div class="sf-suggest-label">Suggested prompts</div>', unsafe_allow_html=True)
    st.markdown('<div class="sf-suggest-zone">', unsafe_allow_html=True)
    sc = st.columns(len(suggestions))
    for i, (icon, label, prompt) in enumerate(suggestions):
        with sc[i]:
            if st.button(f"{icon}  {label}", key=f"coco_sugg_{i}", use_container_width=True):
                coco_generate(prompt)
                _rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Composer ----
    # Prefer native st.chat_input: Enter sends, Shift+Enter inserts a new line.
    has_chat_input = hasattr(st, "chat_input")

    if has_chat_input:
        cc1, cc2 = st.columns([6, 1])
        with cc2:
            if st.button("\U0001F5D1  Clear", key="coco_clear", use_container_width=True):
                st.session_state.chat_messages = []
                _rerun()
        prompt = st.chat_input("Message CoCo\u2026  (Enter to send \u2022 Shift+Enter for a new line)")
        if prompt and prompt.strip():
            coco_generate(prompt.strip())
            _rerun()
    else:
        # Fallback for older Streamlit runtimes without st.chat_input.
        with st.form("coco_chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "Message CoCo",
                height=90,
                placeholder="e.g., What are the fraud signals for ACC-000000000042?",
                label_visibility="collapsed",
            )
            col_send, col_clear = st.columns([5, 1])
            with col_send:
                submitted = st.form_submit_button("\U0001F4E4  Send", use_container_width=True, type="primary")
            with col_clear:
                clear_chat = st.form_submit_button("\U0001F5D1  Clear", use_container_width=True)

        if clear_chat:
            st.session_state.chat_messages = []
            _rerun()
        if submitted and user_input.strip():
            coco_generate(user_input.strip())
            _rerun()


# =============================================================================
# SCREEN 4: REPORT PREVIEW
# =============================================================================
elif screen == "Report Preview":
    st.header("SAR Report Preview")
    st.caption("Generate and preview Suspicious Activity Reports.")

    report_cases = session.sql("""
        SELECT CASE_ID, ACCOUNT_ID, RISK_TIER, ALERT_TYPE, RISK_SCORE
        FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
        WHERE RISK_TIER IN ('HIGH', 'CRITICAL')
        ORDER BY ALERT_TIMESTAMP DESC LIMIT 20
    """).to_pandas()

    if report_cases.empty:
        st.info("No HIGH/CRITICAL cases available for SAR generation.")
    else:
        case_labels = report_cases.apply(
            lambda r: f"{r['CASE_ID']}  \u2022  {r['RISK_TIER']}  \u2022  Score {r['RISK_SCORE']}  \u2022  {r['ACCOUNT_ID']}", axis=1
        ).tolist()
        report_idx = st.selectbox(
            "Select Case for Report",
            range(len(case_labels)),
            format_func=lambda i: case_labels[i],
            help="Only HIGH and CRITICAL cases are eligible for SAR generation.",
        )
        report_case_id = report_cases.iloc[report_idx]["CASE_ID"]

        if st.button("\U0001F4C4  Generate SAR Report", type="primary"):
            with st.spinner("Generating Suspicious Activity Report..."):
                # Build report from data
                report_data = session.sql("""
                    SELECT fa.CASE_ID, fa.ACCOUNT_ID, fa.TXN_ID, fa.ALERT_TYPE,
                           fa.RISK_SCORE, fa.RISK_TIER, fa.CASE_STATUS, fa.ASSIGNED_ANALYST,
                           fa.ALERT_TIMESTAMP,
                           te.AMOUNT, te.MERCHANT, te.GEO_COUNTRY, te.GEO_CITY,
                           te.CHANNEL, te.TXN_TIMESTAMP, te.DEVICE_ID,
                           te.SIGNAL_VELOCITY, te.SIGNAL_AMOUNT_ANOMALY,
                           te.SIGNAL_GEO_MISMATCH, te.SIGNAL_WATCHLIST_MATCH,
                           te.SIGNAL_STRUCTURING, te.SIGNAL_ROUND_NUMBER,
                           te.RISK_SCORE AS TXN_SCORE, te.RISK_TIER AS TXN_TIER,
                           a.KYC_STATUS, a.DOMICILE_COUNTRY, a.ACCOUNT_TYPE, a.ONBOARDING_DATE
                    FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS fa
                    LEFT JOIN FRAUDSHIELD_360_DB.CURATED.TRANSACTION_ENRICHED te ON fa.TXN_ID = te.TXN_ID
                    LEFT JOIN FRAUDSHIELD_360_DB.RAW.RAW_ACCOUNTS a ON fa.ACCOUNT_ID = a.ACCOUNT_ID
                    WHERE fa.CASE_ID = ?
                """, params=[report_case_id]).to_pandas()

                verification_data = session.sql("""
                    SELECT RESPONSE_TYPE, VERIFICATION_METHOD, RESPONSE_TIME_MINUTES,
                           ALERT_DISPATCHED_AT, RESPONSE_TIMESTAMP
                    FROM FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS
                    WHERE CASE_ID = ?
                    ORDER BY ALERT_DISPATCHED_AT DESC LIMIT 1
                """, params=[report_case_id]).to_pandas()

                if not report_data.empty:
                    rd = report_data.iloc[0]
                    vr = verification_data.iloc[0] if not verification_data.empty else {}

                    # Build signals list
                    fired_signals = []
                    if rd.get("SIGNAL_VELOCITY"): fired_signals.append("VELOCITY (>3 txns/hour, weight=15)")
                    if rd.get("SIGNAL_AMOUNT_ANOMALY"): fired_signals.append("AMOUNT_ANOMALY (>5x median, weight=25)")
                    if rd.get("SIGNAL_GEO_MISMATCH"): fired_signals.append("GEO_MISMATCH (country != domicile, weight=20)")
                    if rd.get("SIGNAL_WATCHLIST_MATCH"): fired_signals.append("WATCHLIST_MATCH (entity hit, weight=30)")
                    if rd.get("SIGNAL_STRUCTURING"): fired_signals.append("STRUCTURING ($9K-$9.9K range, weight=20)")
                    if rd.get("SIGNAL_ROUND_NUMBER"): fired_signals.append("ROUND_NUMBER (mod 1000=0, weight=5)")
                    signals_str = "\n".join([f"  - {s}" for s in fired_signals]) if fired_signals else "  - None"

                    response_type = safe_val(vr.get("RESPONSE_TYPE") if isinstance(vr, dict) or hasattr(vr, 'get') else (vr["RESPONSE_TYPE"] if not verification_data.empty else None), "NO_VERIFICATION")

                    amount = rd.get("AMOUNT")
                    amount_str = f"${amount:,.2f}" if pd.notna(amount) else "N/A"

                    report_text = f"""=== SUSPICIOUS ACTIVITY REPORT ===
Case ID: {rd['CASE_ID']}
Generated: Preview Mode

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 1: EXECUTIVE SUMMARY
  Alert Type: {safe_val(rd.get('ALERT_TYPE'))}
  Risk Tier: {safe_val(rd.get('TXN_TIER', rd.get('RISK_TIER')))} (Score: {safe_val(rd.get('TXN_SCORE', rd.get('RISK_SCORE')))}/100)
  Account: {rd.get('ACCOUNT_ID')}
  Amount: {amount_str}
  Recommendation: {'SAR filing required' if safe_val(rd.get('TXN_TIER', rd.get('RISK_TIER'))) in ('CRITICAL', 'HIGH') else 'Continue monitoring'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 2: SUBJECT IDENTIFICATION
  Account ID: {rd.get('ACCOUNT_ID')}
  Account Type: {safe_val(rd.get('ACCOUNT_TYPE'))}
  Domicile: {safe_val(rd.get('DOMICILE_COUNTRY'))}
  Onboarding: {safe_val(rd.get('ONBOARDING_DATE'))}
  KYC Status: {safe_val(rd.get('KYC_STATUS'))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 3: TRANSACTION DETAILS
  TXN ID: {safe_val(rd.get('TXN_ID'))}
  Amount: {amount_str}
  Merchant: {safe_val(rd.get('MERCHANT'))}
  Location: {safe_val(rd.get('GEO_CITY'))}, {safe_val(rd.get('GEO_COUNTRY'))}
  Channel: {safe_val(rd.get('CHANNEL'))}
  Timestamp: {safe_ts(rd.get('TXN_TIMESTAMP'))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 4: EVIDENCE CHAIN
  Triggered Signals:
{signals_str}

  Customer Verification:
  - Status: {response_type}
  - Method: {safe_val(vr.get('VERIFICATION_METHOD') if isinstance(vr, (dict, pd.Series)) else None)}
  - Response Time: {safe_val(vr.get('RESPONSE_TIME_MINUTES') if isinstance(vr, (dict, pd.Series)) else None)} min

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 5: RISK ASSESSMENT
  Composite Score: {safe_val(rd.get('TXN_SCORE', rd.get('RISK_SCORE')))}/100
  Tier: {safe_val(rd.get('TXN_TIER', rd.get('RISK_TIER')))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 6: PATTERN ANALYSIS
  Analyst: {safe_val(rd.get('ASSIGNED_ANALYST'), 'Unassigned')}
  Case Status: {rd.get('CASE_STATUS')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 7: REGULATORY IMPLICATIONS
  {'- Amount >= $10K: CTR threshold (31 CFR 1010.311)' if pd.notna(amount) and amount >= 10000 else ''}
  {'- Structuring suspected (31 USC 5324)' if rd.get('SIGNAL_STRUCTURING') else ''}
  {'- Cross-border EDD required (FATF Rec. 16)' if rd.get('SIGNAL_GEO_MISMATCH') else ''}
  {'- OFAC match: immediate escalation (31 CFR Part 501)' if rd.get('SIGNAL_WATCHLIST_MATCH') else ''}
  - SAR filing recommended within 30 days (31 CFR 1020.320)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 8: RECOMMENDED ACTIONS
  1. Escalate to BSA Officer
  2. Place account on enhanced monitoring (90 days)
  3. Prepare SAR filing within 30 calendar days
  {'4. PRIORITY: Customer rejected transaction - initiate credential reset' if response_type == 'USER_REJECTED' else ''}

=== END OF REPORT ==="""

                    # Persist so the preview + downloads survive the download rerun
                    st.session_state["sar_report"] = {
                        "case_id": str(rd["CASE_ID"]),
                        "text": report_text,
                    }
                else:
                    st.session_state.pop("sar_report", None)
                    st.error("Unable to retrieve case data. Please try a different case.")

        # ---- Persisted preview + download options ----
        sar = st.session_state.get("sar_report")
        if sar:
            st.divider()
            st.warning("**DRAFT** — This report has not been reviewed or filed. Do not distribute.")
            st.text_area("SAR Report", value=sar["text"], height=600, disabled=True)

            safe_cid = "".join(ch if ch.isalnum() else "_" for ch in sar["case_id"])[:40]
            pdf_bytes = build_sar_pdf(sar["text"], sar["case_id"])

            # Downloads served as base64 data URIs (reliable in Streamlit-in-Snowflake;
            # avoids the presigned-URL 'SignatureDoesNotMatch' error from st.download_button).
            links = []
            if pdf_bytes:
                links.append(download_link(
                    "\U0001F4E5&nbsp; Download PDF", pdf_bytes,
                    f"SAR_{safe_cid}.pdf", "application/pdf", primary=True,
                ))
            links.append(download_link(
                "\U0001F4C4&nbsp; Download Text", sar["text"].encode("utf-8"),
                f"SAR_{safe_cid}.txt", "text/plain; charset=utf-8", primary=not bool(pdf_bytes),
            ))
            st.markdown('<div class="sf-dl-row">' + "".join(links) + "</div>", unsafe_allow_html=True)

            if not pdf_bytes:
                st.caption("PDF export requires the **reportlab** package. Add it via the app's **Packages** menu, then regenerate. Text download is always available.")


# =============================================================================
# SCREEN 5: METRICS DASHBOARD
# =============================================================================
elif screen == "Metrics Dashboard":
    st.header("Verification & Risk Metrics")

    metrics_df = session.sql("SELECT * FROM FRAUDSHIELD_360_DB.ANALYTICS.V_VERIFICATION_METRICS").to_pandas()

    if not metrics_df.empty:
        m = metrics_df.iloc[0]

        # Primary KPIs
        st.subheader("Verification KPIs")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Verifications", f"{int(m['TOTAL_VERIFICATIONS_SENT']):,}")
        k2.metric("Acceptance Rate", f"{m['ACCEPTANCE_RATE_PCT']}%")
        k3.metric("Rejection Rate", f"{m['REJECTION_RATE_PCT']}%")
        k4.metric("Avg Response Time", f"{m['AVG_RESPONSE_TIME_MINUTES_EXCL_TIMEOUTS']} min")

        # Secondary KPIs
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Hold Rate", f"{m['HOLD_RATE_PCT']}%")
        s2.metric("Timeout Rate", f"{m['TIMEOUT_RATE_PCT']}%")
        s3.metric("Confirmed Count", f"{int(m['CONFIRMED_COUNT']):,}")

        # SLA Breached count
        sla_df = session.sql("""
            SELECT COUNT(*) AS BREACHED
            FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
            WHERE SLA_DUE_AT < CURRENT_TIMESTAMP()
              AND CASE_STATUS = 'ESCALATED'
        """).to_pandas()
        sla_breached = int(sla_df.iloc[0]["BREACHED"]) if not sla_df.empty else 0
        s4.metric("SLA Breached", sla_breached)

        # Send SLA breach notification if any found (once per session load)
        if sla_breached > 0 and "sla_notif_sent" not in st.session_state:
            try:
                breach_msg = f"SLA BREACH ALERT: {sla_breached} escalated case(s) have exceeded their 8-hour SLA deadline."
                session.sql("""
                    CALL SYSTEM$SEND_EMAIL(
                        'FRAUDSHIELD_EMAIL_INT',
                        'owendrilasaha09@gmail.com',
                        'FraudShield URGENT: SLA Breach Detected',
                        ?
                    )
                """, params=[breach_msg]).collect()
                session.sql("""
                    INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                    (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                    VALUES ('SYSTEM', 'SLA_BREACH_EMAIL_SENT', CURRENT_USER(), ?)
                """, params=[f"{sla_breached} breached cases notified"]).collect()
                st.session_state["sla_notif_sent"] = True
            except Exception as sla_err:
                print(f"[SLA_BREACH_NOTIF_ERROR] {sla_err}")

        st.divider()

        # Response distribution chart
        st.subheader("Response Distribution")
        dist_data = pd.DataFrame({
            "Response Type": ["Confirmed", "Hold/Review", "Rejected", "Timeout"],
            "Count": [
                int(m["CONFIRMED_COUNT"]),
                int(m["REVIEW_COUNT"]),
                int(m["REJECTED_COUNT"]),
                int(m["TIMEOUT_COUNT"])
            ]
        }).set_index("Response Type")
        st.bar_chart(dist_data)

        st.divider()

        # Fraud risk trend
        st.subheader("30-Day Fraud Risk Trend")
        risk_df = session.sql("""
            SELECT METRIC_DATE, FLAG_RATE_PCT, AVG_RISK_SCORE, TOTAL_TRANSACTIONS, FLAGGED_TRANSACTIONS
            FROM FRAUDSHIELD_360_DB.ANALYTICS.V_FRAUD_RISK_DASHBOARD
            ORDER BY METRIC_DATE ASC
            LIMIT 30
        """).to_pandas()

        if not risk_df.empty:
            r1, r2, r3 = st.columns(3)
            r1.metric("Total Txns (30d)", f"{int(risk_df['TOTAL_TRANSACTIONS'].sum()):,}")
            r2.metric("Flagged (30d)", f"{int(risk_df['FLAGGED_TRANSACTIONS'].sum()):,}")
            flag_rate = round(risk_df["FLAGGED_TRANSACTIONS"].sum() * 100.0 / max(risk_df["TOTAL_TRANSACTIONS"].sum(), 1), 2)
            r3.metric("Overall Flag Rate", f"{flag_rate}%")

            st.line_chart(risk_df.set_index("METRIC_DATE")[["FLAG_RATE_PCT"]])
        else:
            st.info("No trend data available yet.")
    else:
        st.warning("No verification metrics available.")


# =============================================================================
# SCREEN 6: AUDIT LOG
# =============================================================================
elif screen == "Audit Log":
    st.header("Audit Log")
    st.caption("Read-only view of all system and user actions. Visible to AUDIT_ROLE and COMPLIANCE_OFFICER_ROLE.")

    # Filters
    af1, af2 = st.columns(2)
    with af1:
        action_filter = st.text_input("Filter by Action (contains)", placeholder="e.g., ESCALAT")
    with af2:
        limit_audit = st.selectbox("Max Rows", [50, 100, 250, 500], index=1)

    if action_filter:
        audit_df = session.sql("""
            SELECT EVENT_ID, CASE_ID, ACTION_TAKEN, ACTOR, EVENT_TIMESTAMP, DETAILS
            FROM FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG_V
            WHERE ACTION_TAKEN ILIKE ?
            LIMIT ?
        """, params=[f"%{action_filter}%", limit_audit]).to_pandas()
    else:
        audit_df = session.sql(f"""
            SELECT EVENT_ID, CASE_ID, ACTION_TAKEN, ACTOR, EVENT_TIMESTAMP, DETAILS
            FROM FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG_V
            LIMIT {int(limit_audit)}
        """).to_pandas()

    if not audit_df.empty:
        st.dataframe(audit_df, use_container_width=True)
        st.caption(f"Showing {len(audit_df)} record(s).")
    else:
        st.info("No audit records found.")


# =============================================================================
# SCREEN 7: ACCESS MANAGEMENT
# =============================================================================
elif screen == "Access Management":
    st.header("Access Management")
    st.caption("User lifecycle, role assignment, maker-checker approval, and offboarding.")

    # Roles that can be assigned from this UI (never the admin role itself)
    ASSIGNABLE_ROLES = sorted(ALLOWED_ROLES - {'FRAUDSHIELD_ACCESS_ADMIN_ROLE'})

    # Fetch account users once
    try:
        users_df = session.sql("SHOW USERS").to_pandas()
        user_list = users_df["name"].tolist() if "name" in users_df.columns else []
    except Exception as e:
        user_list = []
        print(f"[ACCESS_MGMT] SHOW USERS failed: {e}")

    # Current user for self-target blocking
    cu_df = session.sql("SELECT CURRENT_USER() AS U").to_pandas()
    current_user_name = cu_df.iloc[0]["U"] if not cu_df.empty else ""

    # ----- TABS -----
    tab_users, tab_add, tab_assign, tab_requests, tab_offboard = st.tabs([
        "Users", "Add User", "Assign/Revoke Role", "Access Requests", "Offboard"
    ])

    # ===== TAB 1: USERS =====
    with tab_users:
        st.subheader("Current Users & Roles")
        mappings_df = session.sql("""
            SELECT USER_NAME, ASSIGNED_ROLE, STATUS, ASSIGNED_BY, ASSIGNED_AT, EXPIRES_AT
            FROM FRAUDSHIELD_360_DB.AGENTS.USER_ROLE_MAPPING
            ORDER BY USER_NAME, ASSIGNED_ROLE
        """).to_pandas()
        if not mappings_df.empty:
            st.dataframe(mappings_df, use_container_width=True)
        else:
            st.info("No user-role mappings found.")

    # ===== TAB 2: ADD USER =====
    with tab_add:
        st.subheader("Create New User")
        with st.form("add_user_form"):
            new_login = st.text_input("Login Name", placeholder="e.g., john_analyst")
            new_display = st.text_input("Display Name", placeholder="e.g., John Smith")
            new_email = st.text_input("Email", placeholder="user@company.com")
            new_role = st.selectbox("Initial Role", ASSIGNABLE_ROLES)
            add_submitted = st.form_submit_button("Create User")

        if add_submitted:
            try:
                _validate_identifier(new_login)
                _validate_identifier(new_role)
                if not new_email or "@" not in new_email:
                    raise ValueError("Invalid email address")
                # Validate display name (allow spaces and common chars)
                if new_display and not _re.match(r'^[A-Za-z0-9 _.\-]{1,255}$', new_display):
                    raise ValueError("Display name contains invalid characters")

                safe_display = new_display.replace("'", "''") if new_display else new_login
                safe_email = new_email.replace("'", "''")

                session.sql(f"""
                    CREATE USER IF NOT EXISTS "{new_login}"
                    PASSWORD = 'ChangeMeNow1!'
                    MUST_CHANGE_PASSWORD = TRUE
                    DEFAULT_ROLE = '{new_role}'
                    DISPLAY_NAME = '{safe_display}'
                    EMAIL = '{safe_email}'
                """).collect()
                session.sql(f'GRANT ROLE {new_role} TO USER "{new_login}"').collect()
                session.sql("""
                    MERGE INTO FRAUDSHIELD_360_DB.AGENTS.USER_ROLE_MAPPING tgt
                    USING (SELECT ? AS UN, ? AS AR) src
                    ON tgt.USER_NAME = src.UN AND tgt.ASSIGNED_ROLE = src.AR
                    WHEN MATCHED THEN UPDATE SET STATUS = 'ACTIVE', ASSIGNED_BY = CURRENT_USER(), ASSIGNED_AT = CURRENT_TIMESTAMP()
                    WHEN NOT MATCHED THEN INSERT (USER_NAME, ASSIGNED_ROLE, ASSIGNED_BY, STATUS)
                        VALUES (src.UN, src.AR, CURRENT_USER(), 'ACTIVE')
                """, params=[new_login, new_role]).collect()
                session.sql("""
                    INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                    (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                    VALUES ('SYSTEM', 'USER_CREATED', CURRENT_USER(), ?)
                """, params=[f"Created user {new_login} with role {new_role}"]).collect()
                st.success(f"User **{new_login}** created with role **{new_role}** (must change password on first login).")
            except ValueError as ve:
                print(f"[ADD_USER_VALIDATION] {ve}")
                st.error(f"Validation error: {str(ve)}")
            except Exception as e:
                print(f"[ADD_USER_ERROR] {e}")
                st.error(f"Failed to create user: {str(e)}")

    # ===== TAB 3: ASSIGN/REVOKE ROLE =====
    with tab_assign:
        st.subheader("Assign or Revoke Role")
        if not user_list:
            st.warning("No users available.")
        else:
            with st.form("assign_revoke_form"):
                target_user = st.selectbox("Target User", user_list)
                target_role = st.selectbox("Role", ASSIGNABLE_ROLES)
                col_g, col_r = st.columns(2)
                with col_g:
                    do_grant = st.form_submit_button("Grant Role")
                with col_r:
                    do_revoke = st.form_submit_button("Revoke Role")

            if do_grant or do_revoke:
                action = "GRANT" if do_grant else "REVOKE"
                try:
                    _validate_identifier(target_user)
                    _validate_identifier(target_role)
                    if target_role not in ALLOWED_ROLES or target_role == 'FRAUDSHIELD_ACCESS_ADMIN_ROLE':
                        raise ValueError("Cannot assign admin role from app")
                    if target_user == current_user_name:
                        st.error("You cannot modify your own role assignments.")
                        st.stop()

                    if do_grant and target_role == "COMPLIANCE_OFFICER_ROLE":
                        # Maker-checker: queue for approval
                        session.sql("""
                            INSERT INTO FRAUDSHIELD_360_DB.AGENTS.ACCESS_REQUESTS
                            (TARGET_USER, REQUESTED_ROLE, REQUESTED_BY, STATUS)
                            VALUES (?, ?, CURRENT_USER(), 'PENDING')
                        """, params=[target_user, target_role]).collect()
                        session.sql("""
                            INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                            (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                            VALUES ('SYSTEM', 'ACCESS_REQUEST_CREATED', CURRENT_USER(), ?)
                        """, params=[f"Requested {target_role} for {target_user} - pending approval"]).collect()
                        st.info(f"**COMPLIANCE_OFFICER_ROLE** requires maker-checker approval. Request submitted for **{target_user}**.")
                    elif do_grant:
                        session.sql(f'GRANT ROLE {target_role} TO USER "{target_user}"').collect()
                        session.sql("""
                            MERGE INTO FRAUDSHIELD_360_DB.AGENTS.USER_ROLE_MAPPING tgt
                            USING (SELECT ? AS UN, ? AS AR) src
                            ON tgt.USER_NAME = src.UN AND tgt.ASSIGNED_ROLE = src.AR
                            WHEN MATCHED THEN UPDATE SET STATUS = 'ACTIVE', ASSIGNED_BY = CURRENT_USER(), ASSIGNED_AT = CURRENT_TIMESTAMP()
                            WHEN NOT MATCHED THEN INSERT (USER_NAME, ASSIGNED_ROLE, ASSIGNED_BY, STATUS)
                                VALUES (src.UN, src.AR, CURRENT_USER(), 'ACTIVE')
                        """, params=[target_user, target_role]).collect()
                        session.sql("""
                            INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                            (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                            VALUES ('SYSTEM', 'ROLE_GRANTED', CURRENT_USER(), ?)
                        """, params=[f"Granted {target_role} to {target_user}"]).collect()
                        st.success(f"Role **{target_role}** granted to **{target_user}**.")
                    else:
                        session.sql(f'REVOKE ROLE {target_role} FROM USER "{target_user}"').collect()
                        session.sql("""
                            UPDATE FRAUDSHIELD_360_DB.AGENTS.USER_ROLE_MAPPING
                            SET STATUS = 'REVOKED', ASSIGNED_AT = CURRENT_TIMESTAMP()
                            WHERE USER_NAME = ? AND ASSIGNED_ROLE = ?
                        """, params=[target_user, target_role]).collect()
                        session.sql("""
                            INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                            (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                            VALUES ('SYSTEM', 'ROLE_REVOKED', CURRENT_USER(), ?)
                        """, params=[f"Revoked {target_role} from {target_user}"]).collect()
                        st.success(f"Role **{target_role}** revoked from **{target_user}**.")
                except ValueError as ve:
                    print(f"[ASSIGN_REVOKE_VALIDATION] {ve}")
                    st.error("Invalid input or disallowed operation.")
                except Exception as e:
                    print(f"[ASSIGN_REVOKE_ERROR] action={action} error={e}")
                    st.error("Operation failed. Check privileges and try again.")

    # ===== TAB 4: ACCESS REQUESTS (Maker-Checker) =====
    with tab_requests:
        st.subheader("Pending Access Requests")
        st.caption("COMPLIANCE_OFFICER_ROLE grants require a different admin to approve.")
        pending_df = session.sql("""
            SELECT REQUEST_ID, TARGET_USER, REQUESTED_ROLE, REQUESTED_BY, REQUESTED_AT
            FROM FRAUDSHIELD_360_DB.AGENTS.ACCESS_REQUESTS
            WHERE STATUS = 'PENDING'
            ORDER BY REQUESTED_AT ASC
        """).to_pandas()

        if pending_df.empty:
            st.info("No pending access requests.")
        else:
            for idx, req in pending_df.iterrows():
                with st.expander(f"{req['TARGET_USER']} -> {req['REQUESTED_ROLE']} (by {req['REQUESTED_BY']})"):
                    st.write(f"**Requested At:** {req['REQUESTED_AT']}")
                    if req["REQUESTED_BY"] == current_user_name:
                        st.warning("You cannot approve your own request. Another admin must approve.")
                    else:
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Approve", key=f"appr_{req['REQUEST_ID']}"):
                                try:
                                    t_user = req["TARGET_USER"]
                                    t_role = req["REQUESTED_ROLE"]
                                    _validate_identifier(t_user)
                                    _validate_identifier(t_role)
                                    session.sql(f'GRANT ROLE {t_role} TO USER "{t_user}"').collect()
                                    session.sql("""
                                        MERGE INTO FRAUDSHIELD_360_DB.AGENTS.USER_ROLE_MAPPING tgt
                                        USING (SELECT ? AS UN, ? AS AR) src
                                        ON tgt.USER_NAME = src.UN AND tgt.ASSIGNED_ROLE = src.AR
                                        WHEN MATCHED THEN UPDATE SET STATUS = 'ACTIVE', ASSIGNED_BY = CURRENT_USER(), ASSIGNED_AT = CURRENT_TIMESTAMP()
                                        WHEN NOT MATCHED THEN INSERT (USER_NAME, ASSIGNED_ROLE, ASSIGNED_BY, STATUS)
                                            VALUES (src.UN, src.AR, CURRENT_USER(), 'ACTIVE')
                                    """, params=[t_user, t_role]).collect()
                                    session.sql("""
                                        UPDATE FRAUDSHIELD_360_DB.AGENTS.ACCESS_REQUESTS
                                        SET STATUS = 'APPROVED', APPROVED_BY = CURRENT_USER(), APPROVED_AT = CURRENT_TIMESTAMP()
                                        WHERE REQUEST_ID = ?
                                    """, params=[req["REQUEST_ID"]]).collect()
                                    session.sql("""
                                        INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                                        (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                                        VALUES ('SYSTEM', 'ACCESS_REQUEST_APPROVED', CURRENT_USER(), ?)
                                    """, params=[f"Approved {t_role} for {t_user}"]).collect()
                                    st.success("Request approved.")
                                    _rerun()
                                except Exception as e:
                                    print(f"[APPROVE_ERROR] {e}")
                                    st.error("Approval failed.")
                        with c2:
                            if st.button("Deny", key=f"deny_{req['REQUEST_ID']}"):
                                try:
                                    session.sql("""
                                        UPDATE FRAUDSHIELD_360_DB.AGENTS.ACCESS_REQUESTS
                                        SET STATUS = 'DENIED', APPROVED_BY = CURRENT_USER(), APPROVED_AT = CURRENT_TIMESTAMP()
                                        WHERE REQUEST_ID = ?
                                    """, params=[req["REQUEST_ID"]]).collect()
                                    session.sql("""
                                        INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                                        (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                                        VALUES ('SYSTEM', 'ACCESS_REQUEST_DENIED', CURRENT_USER(), ?)
                                    """, params=[f"Denied {req['REQUESTED_ROLE']} for {req['TARGET_USER']}"]).collect()
                                    st.warning("Request denied.")
                                    _rerun()
                                except Exception as e:
                                    print(f"[DENY_ERROR] {e}")
                                    st.error("Denial failed.")

    # ===== TAB 5: OFFBOARD =====
    with tab_offboard:
        st.subheader("Offboard User")
        st.caption("Disable a user account and revoke all FraudShield role mappings.")
        if not user_list:
            st.warning("No users available.")
        else:
            with st.form("offboard_form"):
                offboard_user = st.selectbox("User to Offboard", [u for u in user_list if u != current_user_name])
                offboard_confirm = st.checkbox("I confirm this user should be disabled and all access revoked.")
                offboard_submitted = st.form_submit_button("Offboard User")

            if offboard_submitted:
                if not offboard_confirm:
                    st.error("You must confirm the offboarding action.")
                else:
                    try:
                        _validate_identifier(offboard_user)
                        session.sql(f'ALTER USER "{offboard_user}" SET DISABLED = TRUE').collect()
                        session.sql("""
                            UPDATE FRAUDSHIELD_360_DB.AGENTS.USER_ROLE_MAPPING
                            SET STATUS = 'REVOKED', ASSIGNED_AT = CURRENT_TIMESTAMP()
                            WHERE USER_NAME = ? AND STATUS = 'ACTIVE'
                        """, params=[offboard_user]).collect()
                        session.sql("""
                            INSERT INTO FRAUDSHIELD_360_DB.AGENTS.AGENT_AUDIT_LOG
                            (CASE_ID, ACTION_TAKEN, RESOLVED_BY, REVIEWER_NOTES)
                            VALUES ('SYSTEM', 'USER_OFFBOARDED', CURRENT_USER(), ?)
                        """, params=[f"Disabled user {offboard_user} and revoked all roles"]).collect()
                        st.success(f"User **{offboard_user}** has been disabled and all access revoked.")
                    except ValueError as ve:
                        print(f"[OFFBOARD_VALIDATION] {ve}")
                        st.error("Invalid user identifier.")
                    except Exception as e:
                        print(f"[OFFBOARD_ERROR] user={offboard_user} error={e}")
                        st.error("Offboarding failed. Check privileges.")
