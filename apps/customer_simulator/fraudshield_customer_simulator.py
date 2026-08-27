"""
FraudShield 360 — Customer Simulator
Production-grade Streamlit-in-Snowflake application.

Compatibility: written to run on Streamlit 1.22.0 (Snowflake default) as well
as newer releases. No 1.23+ only widgets are used; query params are read via a
version-agnostic shim.

Capabilities
------------
1. Account Settings ... configure a simulated customer profile (+ SHA2 hashes).
2. Send Money ......... simulate a payment; high-risk payments raise a fraud
                        case, a verification event, and a branded HTML email.
3. Verification Inbox . respond (Accept / Hold / Reject) in-app.
4. Email-link handler . the same responses can be actioned from the email
                        buttons via single-use, expiring URL tokens.

Engineering principles
----------------------
* Zero string-interpolated SQL — every statement uses bound parameters.
* Multi-table writes wrapped in BEGIN / COMMIT / ROLLBACK (atomic).
* Single-use, time-boxed verification tokens (never expose EVENT_ID as secret).
* Confirmation-on-POST pattern so email link-scanners can't auto-trigger actions.
* Centralized config, a thin data-access layer, cached reference reads.

Prerequisite (run once in a worksheet):
    ALTER TABLE FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS
      ADD COLUMN IF NOT EXISTS VERIFICATION_TOKEN STRING,
          COLUMN IF NOT EXISTS TOKEN_EXPIRES_AT   TIMESTAMP_NTZ;
"""

import re
import uuid
import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.exceptions import SnowparkSQLException

# =============================================================================
# CONFIGURATION
# =============================================================================
DB     = "FRAUDSHIELD_360_DB"
RAW    = f"{DB}.RAW"
AGENTS = f"{DB}.AGENTS"

EMAIL_INTEGRATION = "FRAUDSHIELD_EMAIL_INT"
TOKEN_TTL_MINUTES = 30

# The running URL of THIS Streamlit-in-Snowflake app (strip the trailing /edit).
# Email buttons link back here; SiS populates query params on click.
APP_BASE_URL = (
    "https://app.snowflake.com/ap-southeast-7.aws/tv48944/"
    "#/streamlit-apps/FRAUDSHIELD_360_DB.AGENTS.FRAUDSHIELD_CUSTOMER_SIMULATOR"
)

# Simple risk heuristic (real scoring belongs in a UDF / model / stream+task).
HIGH_RISK_AMOUNT    = 9000.00
HIGH_RISK_COUNTRIES = {"NG", "RU", "KY", "PA", "IR"}

COUNTRIES = ["US", "GB", "DE", "FR", "JP", "NG", "RU", "KY",
             "PA", "IR", "CN", "AE", "SG", "AU", "CA"]
CHANNELS  = ["MOBILE_APP", "WEB", "POS", "ATM", "API"]

# action -> (verification response type, resulting case status, st.<style> fn)
ACTION_MAP = {
    "accept": ("USER_CONFIRMED",        "RESOLVED_CONFIRMED", "success"),
    "hold":   ("USER_REQUESTED_REVIEW", "UNDER_REVIEW",       "warning"),
    "reject": ("USER_REJECTED",         "ESCALATED",          "error"),
}
ACTION_MSG = {
    "accept": "Transaction confirmed. Alert resolved.",
    "hold":   "Transaction placed on hold for analyst review.",
    "reject": "Transaction rejected. Case escalated to fraud team.",
}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9\-\s()]{7,20}$")

# =============================================================================
# PAGE + THEME
# =============================================================================
st.set_page_config(
    page_title="FraudShield 360 — Customer Simulator",
    page_icon="🛡️",
    layout="wide",
)

st.markdown(
    """
    <style>
      :root{
        --sf-blue:#29B5E8; --sf-navy:#11567F; --sf-ink:#1E2A32;
        --sf-mute:#5B6B77; --sf-line:#E3E9ED;
      }
      .block-container{ padding-top:2.2rem; max-width:1200px; }
      h1,h2,h3{ color:var(--sf-navy); font-weight:700; letter-spacing:-.01em; }
      .sf-hero{
        background:linear-gradient(120deg,var(--sf-navy) 0%,var(--sf-blue) 100%);
        color:#fff; padding:1.4rem 1.6rem; border-radius:14px; margin-bottom:1.4rem;
      }
      .sf-hero h1{ color:#fff; margin:0; font-size:1.6rem; }
      .sf-hero p{ color:rgba(255,255,255,.85); margin:.25rem 0 0; font-size:.95rem; }
      .sf-pill{ display:inline-block; padding:.15rem .6rem; border-radius:999px;
                font-size:.72rem; font-weight:600; letter-spacing:.02em; }
      .pill-critical{ background:#FDECEC; color:#B3261E; }
      .pill-open{ background:#E7F5FB; color:var(--sf-navy); }
      .stButton>button{ border-radius:8px; font-weight:600; border:1px solid var(--sf-line); }
      .stTabs [data-baseweb="tab-list"]{ gap:.35rem; }
      .stTabs [data-baseweb="tab"]{ font-weight:600; }
      [data-testid="stMetricValue"]{ color:var(--sf-navy); }
      .sf-mono{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.85rem; }
      .sf-rule{ border:0; border-top:1px solid var(--sf-line); margin:1rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

session = get_active_session()


# =============================================================================
# SMALL COMPATIBILITY HELPERS (Streamlit 1.22-safe)
# =============================================================================
def rule() -> None:
    """Horizontal rule (st.divider() not available before 1.23)."""
    st.markdown("<hr class='sf-rule'/>", unsafe_allow_html=True)


def get_query_params() -> dict:
    """Flat {key: value} query params across Streamlit versions."""
    if hasattr(st, "query_params"):  # Streamlit >= 1.30
        return {k: st.query_params.get(k) for k in st.query_params.keys()}
    raw = st.experimental_get_query_params()  # Streamlit < 1.30 -> {key: [values]}
    return {k: (v[0] if isinstance(v, list) and v else v) for k, v in raw.items()}


def rerun() -> None:
    """Rerun across Streamlit versions."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# =============================================================================
# DATA ACCESS LAYER  (all parameterized — no string interpolation into SQL)
# =============================================================================
def q(sql: str, params=None) -> pd.DataFrame:
    return session.sql(sql, params=params or []).to_pandas()


def exec_sql(sql: str, params=None) -> None:
    session.sql(sql, params=params or []).collect()


@st.cache_data(ttl=60, show_spinner=False)
def load_accounts() -> pd.DataFrame:
    return q(f"SELECT ACCOUNT_ID FROM {RAW}.RAW_ACCOUNTS ORDER BY ACCOUNT_ID LIMIT 200")


def load_account_profile(account_id: str) -> dict:
    df = q(
        f"""SELECT CUSTOMER_NAME, PHONE_NUMBER, EMAIL_ADDRESS
              FROM {RAW}.RAW_ACCOUNTS WHERE ACCOUNT_ID = ?""",
        [account_id],
    )
    if df.empty:
        return {"name": "", "phone": "", "email": ""}
    r = df.iloc[0]
    return {
        "name":  r["CUSTOMER_NAME"] or "",
        "phone": r["PHONE_NUMBER"]  or "",
        "email": r["EMAIL_ADDRESS"] or "",
    }


def save_account_profile(account_id, name, phone, email) -> None:
    exec_sql(
        f"""
        UPDATE {RAW}.RAW_ACCOUNTS
           SET CUSTOMER_NAME          = ?,
               PHONE_NUMBER           = ?,
               EMAIL_ADDRESS          = ?,
               CUSTOMER_NAME_HASH     = SHA2(?),
               REGISTERED_EMAIL_HASH  = SHA2(?),
               REGISTERED_MOBILE_HASH = SHA2(?)
         WHERE ACCOUNT_ID = ?
        """,
        [name, phone, email, name, email, phone, account_id],
    )


def insert_transaction(txn_id, account_id, amount, merchant, country, channel) -> None:
    exec_sql(
        f"""
        INSERT INTO {RAW}.RAW_TRANSACTIONS
            (TXN_ID, ACCOUNT_ID, AMOUNT, MERCHANT, GEO_COUNTRY, GEO_CITY,
             CHANNEL, TXN_TIMESTAMP, DEVICE_ID)
        VALUES (?, ?, ?, ?, ?, 'Simulated', ?, CURRENT_TIMESTAMP(), 'SIMULATOR-DEVICE-001')
        """,
        [txn_id, account_id, amount, merchant, country, channel],
    )


def create_alert_and_verification(account_id, txn_id, explanation):
    """Atomically create fraud alert + verification event. Returns (case_id, event_id, token)."""
    case_id  = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    token    = uuid.uuid4().hex  # single-use secret, distinct from EVENT_ID

    try:
        exec_sql("BEGIN")
        exec_sql(
            f"""
            INSERT INTO {AGENTS}.FRAUD_ALERTS
                (CASE_ID, ACCOUNT_ID, TXN_ID, ALERT_TIMESTAMP, ALERT_TYPE,
                 RISK_SCORE, RISK_TIER, CASE_STATUS)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP(), 'SIMULATOR_ALERT', 75, 'CRITICAL', 'OPEN')
            """,
            [case_id, account_id, txn_id],
        )
        exec_sql(
            f"""
            INSERT INTO {AGENTS}.CUSTOMER_VERIFICATION_EVENTS
                (EVENT_ID, CASE_ID, ACCOUNT_ID, TXN_ID, VERIFICATION_METHOD,
                 RESPONSE_TYPE, ALERT_DISPATCHED_AT, EMAIL_STATUS, PUSH_STATUS,
                 TOKEN_VALID, EXPLANATION_CUSTOMER, VERIFICATION_TOKEN, TOKEN_EXPIRES_AT)
            VALUES (?, ?, ?, ?, 'MULTI_CHANNEL', 'AWAITING_RESPONSE',
                    CURRENT_TIMESTAMP(), 'SENT', 'SENT', TRUE, ?, ?,
                    DATEADD('minute', ?, CURRENT_TIMESTAMP()))
            """,
            [event_id, case_id, account_id, txn_id, explanation, token, TOKEN_TTL_MINUTES],
        )
        exec_sql("COMMIT")
        return case_id, event_id, token
    except SnowparkSQLException:
        exec_sql("ROLLBACK")
        raise


def load_pending(account_id: str) -> pd.DataFrame:
    return q(
        f"""
        SELECT EVENT_ID, TXN_ID, CASE_ID, EXPLANATION_CUSTOMER,
               ALERT_DISPATCHED_AT, VERIFICATION_METHOD
          FROM {AGENTS}.CUSTOMER_VERIFICATION_EVENTS
         WHERE ACCOUNT_ID = ?
           AND RESPONSE_TYPE = 'AWAITING_RESPONSE'
           AND TOKEN_VALID = TRUE
         ORDER BY ALERT_DISPATCHED_AT DESC
        """,
        [account_id],
    )


def validate_token(event_id: str, token: str):
    """Return CASE_ID if the token is valid, active and unexpired; else None."""
    df = q(
        f"""SELECT CASE_ID
              FROM {AGENTS}.CUSTOMER_VERIFICATION_EVENTS
             WHERE EVENT_ID = ?
               AND VERIFICATION_TOKEN = ?
               AND TOKEN_VALID = TRUE
               AND TOKEN_EXPIRES_AT >= CURRENT_TIMESTAMP()""",
        [event_id, token],
    )
    return None if df.empty else df["CASE_ID"].iloc[0]


def apply_response(event_id: str, case_id: str, action: str) -> None:
    """Atomically record the customer's response across both tables (idempotent guard)."""
    resp_type, case_status, _ = ACTION_MAP[action]
    try:
        exec_sql("BEGIN")
        exec_sql(
            f"""
            UPDATE {AGENTS}.CUSTOMER_VERIFICATION_EVENTS
               SET RESPONSE_TYPE = ?,
                   RESPONSE_TIMESTAMP = CURRENT_TIMESTAMP(),
                   TOKEN_VALID = FALSE
             WHERE EVENT_ID = ? AND TOKEN_VALID = TRUE
            """,
            [resp_type, event_id],
        )
        exec_sql(
            f"UPDATE {AGENTS}.FRAUD_ALERTS SET CASE_STATUS = ? WHERE CASE_ID = ?",
            [case_status, case_id],
        )
        exec_sql("COMMIT")
    except SnowparkSQLException:
        exec_sql("ROLLBACK")
        raise


def send_email(recipient: str, subject: str, html_body: str) -> None:
    exec_sql(
        "CALL SYSTEM$SEND_EMAIL(?, ?, ?, ?, 'text/html')",
        [EMAIL_INTEGRATION, recipient, subject, html_body],
    )


# =============================================================================
# EMAIL TEMPLATE
# =============================================================================
def build_email(amount, merchant, country, event_id, token):
    subject = f"Security check: verify your ${amount:,.2f} payment to {merchant}"

    def btn(action, label, color):
        href = f"{APP_BASE_URL}?e={event_id}&t={token}&a={action}"
        return (
            f'<a href="{href}" style="display:inline-block;margin:4px 6px;padding:11px 20px;'
            f'border-radius:8px;background:{color};color:#fff;text-decoration:none;'
            f'font-weight:600;">{label}</a>'
        )

    html = f"""
    <div style="font-family:Segoe UI,Arial,sans-serif;max-width:520px;margin:auto;
                border:1px solid #E3E9ED;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(120deg,#11567F,#29B5E8);padding:18px 22px;color:#fff;">
        <h2 style="margin:0;font-size:18px;">🛡️ FraudShield 360</h2>
      </div>
      <div style="padding:22px;color:#1E2A32;">
        <p>We noticed an unusual transaction on your account:</p>
        <table style="width:100%;font-size:14px;border-collapse:collapse;">
          <tr><td style="color:#5B6B77;padding:4px 0;">Amount</td>
              <td style="text-align:right;font-weight:600;">${amount:,.2f}</td></tr>
          <tr><td style="color:#5B6B77;padding:4px 0;">Merchant</td>
              <td style="text-align:right;font-weight:600;">{merchant}</td></tr>
          <tr><td style="color:#5B6B77;padding:4px 0;">Destination</td>
              <td style="text-align:right;font-weight:600;">{country}</td></tr>
        </table>
        <p style="margin-top:18px;">Was this you?</p>
        <div style="text-align:center;margin:14px 0;">
          {btn('accept','&#10003; Yes, it was me','#2E7D32')}
          {btn('hold','&#9208; Not sure','#F9A825')}
          {btn('reject','&#10007; No, block it','#C62828')}
        </div>
        <p style="font-size:12px;color:#5B6B77;">
          This link expires in {TOKEN_TTL_MINUTES} minutes and can be used once.
          If you didn&rsquo;t initiate this, choose &ldquo;No, block it&rdquo;.
        </p>
      </div>
    </div>
    """
    return subject, html


# =============================================================================
# EMAIL-LINK HANDLER  (runs FIRST — customer clicked a button in the email)
# =============================================================================
def handle_email_action() -> None:
    p = get_query_params()
    if not ("e" in p and "a" in p):
        return  # normal load, no action encoded in the URL

    event_id = p["e"]
    token    = p.get("t", "")
    action   = p["a"]

    st.markdown(
        '<div class="sf-hero"><h1>🛡️ FraudShield 360</h1>'
        '<p>Verification response</p></div>',
        unsafe_allow_html=True,
    )

    if action not in ACTION_MAP:
        st.error("Invalid verification action.")
        st.stop()

    case_id = validate_token(event_id, token)
    if case_id is None:
        st.warning("This verification link has expired or was already used.")
        st.stop()

    intent = {
        "accept": "confirm this transaction",
        "hold":   "place this transaction on hold for review",
        "reject": "reject and block this transaction",
    }[action]

    # Confirmation-on-POST: never act on the raw page load (email scanners pre-fetch links).
    st.info(f"You are about to **{intent}**.")
    if st.button("Confirm my response", type="primary"):
        try:
            apply_response(event_id, case_id, action)
            getattr(st, ACTION_MAP[action][2])(
                "✅ Your response has been recorded. You may close this page."
            )
        except SnowparkSQLException as e:
            st.error(f"Could not record your response: {e}")
    st.stop()  # do not render the simulator while handling an email click


handle_email_action()

# =============================================================================
# SESSION STATE + HEADER
# =============================================================================
if "account_id" not in st.session_state:
    st.session_state.account_id = None

st.markdown(
    """
    <div class="sf-hero">
      <h1>FraudShield 360 — Customer Simulator</h1>
      <p>Configure a customer profile, simulate payments, and exercise the fraud
         verification workflow end-to-end.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

accounts_df = load_accounts()
if accounts_df.empty:
    st.error("No accounts found in RAW.RAW_ACCOUNTS. Load seed data to continue.")
    st.stop()

with st.sidebar:
    st.markdown("### 🔐 Active Account")
    account_list = accounts_df["ACCOUNT_ID"].tolist()
    default_idx = (
        account_list.index(st.session_state.account_id)
        if st.session_state.account_id in account_list else 0
    )
    st.session_state.account_id = st.selectbox("Account ID", account_list, index=default_idx)
    prof = load_account_profile(st.session_state.account_id)
    st.caption(f"👤 {prof['name']  or '—'}")
    st.caption(f"✉️ {prof['email'] or '—'}")
    rule()
    st.caption("FraudShield 360 · internal simulator")

account_id = st.session_state.account_id
tab1, tab2, tab3 = st.tabs(["⚙️  Account Settings", "💸  Send Money", "📥  Verification Inbox"])

# =============================================================================
# TAB 1 — ACCOUNT SETTINGS
# =============================================================================
with tab1:
    st.subheader("Account Settings")
    st.caption("Configure the simulated customer profile. Values are also stored as SHA2 hashes.")

    profile = load_account_profile(account_id)
    with st.form("account_settings_form"):
        c1, c2 = st.columns(2)
        with c1:
            name_input  = st.text_input("Customer Name", value=profile["name"])
            phone_input = st.text_input("Phone Number", value=profile["phone"],
                                        placeholder="+1-555-0123")
        with c2:
            email_input = st.text_input("Email Address", value=profile["email"],
                                        placeholder="user@example.com")
        saved = st.form_submit_button("💾  Save Settings")

    if saved:
        errors = []
        if not name_input.strip():
            errors.append("Customer name is required.")
        if email_input and not EMAIL_RE.match(email_input):
            errors.append("Email address is not valid.")
        if phone_input and not PHONE_RE.match(phone_input):
            errors.append("Phone number is not valid.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                save_account_profile(account_id, name_input.strip(),
                                     phone_input.strip(), email_input.strip())
                load_accounts.clear()
                st.success(f"Account **{account_id}** updated successfully.")
            except SnowparkSQLException as e:
                st.error(f"Could not save profile: {e}")

# =============================================================================
# TAB 2 — SEND MONEY
# =============================================================================
with tab2:
    st.subheader("Send Money")
    st.caption(f"Simulating a transaction for account **{account_id}**.")

    with st.form("send_money_form"):
        c1, c2 = st.columns(2)
        with c1:
            amount   = st.number_input("Amount ($)", min_value=1.00, max_value=999999.99,
                                       value=150.00, step=0.01, format="%.2f")
            merchant = st.text_input("Merchant", value="Amazon", max_chars=100)
        with c2:
            country = st.selectbox("Destination Country", COUNTRIES)
            channel = st.selectbox("Channel", CHANNELS)

        will_flag = amount >= HIGH_RISK_AMOUNT or country in HIGH_RISK_COUNTRIES
        st.caption(
            "Risk preview: "
            + ("🔴 **HIGH** — verification will be dispatched" if will_flag else "🟢 Normal")
        )
        send_submitted = st.form_submit_button("🚀  Submit Transaction")

    if send_submitted:
        if not merchant.strip():
            st.error("Merchant is required.")
            st.stop()

        txn_id = str(uuid.uuid4())
        try:
            insert_transaction(txn_id, account_id, amount, merchant.strip(), country, channel)
            st.success(f"Transaction submitted · `{txn_id}`")
        except SnowparkSQLException as e:
            st.error(f"Transaction failed: {e}")
            st.stop()

        if not will_flag:
            st.info("✅ Transaction processed. No fraud signals triggered.")
        else:
            st.warning("⚠️ High-risk transaction detected. Dispatching verification…")
            explanation = (
                f"We noticed an unusual transaction of ${amount:,.2f} to "
                f"{merchant.strip()} in {country}. Please confirm this was you."
            )
            try:
                case_id, event_id, token = create_alert_and_verification(
                    account_id, txn_id, explanation
                )
                st.success(f"Verification case created · `{case_id[:8]}…`")
            except SnowparkSQLException as e:
                st.error(f"Could not create verification case: {e}")
                st.stop()

            recipient = load_account_profile(account_id)["email"]
            if not recipient:
                st.info("No email on file — set one in **Account Settings** to receive alerts.")
            else:
                subject, html = build_email(amount, merchant.strip(), country, event_id, token)
                try:
                    send_email(recipient, subject, html)
                    st.info(f"📧 Verification email sent to `{recipient}`.")
                except SnowparkSQLException as e:
                    st.error(
                        "Email dispatch failed. Ensure the recipient is on the "
                        f"integration's ALLOWED_RECIPIENTS. Details: {e}"
                    )

# =============================================================================
# TAB 3 — VERIFICATION INBOX
# =============================================================================
with tab3:
    st.subheader("Verification Inbox")
    st.caption(f"Pending verifications for account **{account_id}**.")

    pending = load_pending(account_id)
    st.metric("Pending", len(pending))

    if pending.empty:
        st.success("🎉 No pending verification requests. Your account is clear.")
    else:
        for _, row in pending.iterrows():
            with st.container():
                rule()
                top = st.columns([3, 1])
                with top[0]:
                    st.markdown(
                        f"**Case** <span class='sf-mono'>{row['CASE_ID'][:8]}…</span> "
                        f"<span class='sf-pill pill-critical'>CRITICAL</span> "
                        f"<span class='sf-pill pill-open'>OPEN</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"<span class='sf-mono'>Txn {row['TXN_ID']}</span>",
                                unsafe_allow_html=True)
                with top[1]:
                    st.caption(f"🕒 {row['ALERT_DISPATCHED_AT']}")

                st.info(row["EXPLANATION_CUSTOMER"] or "Please verify this transaction.")

                cols = st.columns(3)
                buttons = [
                    (cols[0], "accept", "✓ Accept", "primary"),
                    (cols[1], "hold",   "⏸ Hold",   "secondary"),
                    (cols[2], "reject", "✕ Reject", "secondary"),
                ]
                for col, action, label, btype in buttons:
                    if col.button(label, key=f"{action}_{row['EVENT_ID']}",
                                  type=btype, use_container_width=True):
                        try:
                            apply_response(row["EVENT_ID"], row["CASE_ID"], action)
                            getattr(st, ACTION_MAP[action][2])(ACTION_MSG[action])
                            rerun()
                        except SnowparkSQLException as e:
                            st.error(f"Could not record response: {e}")
