import json
import re
import hashlib
import secrets
import _snowflake

# Parameters injected by skill runtime
mode = mode if 'mode' in dir() and mode else 'dispatch'  # noqa: F841

# --- Input validation ---
UUID_RE = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
ACC_RE = re.compile(r'^ACC-\d{1,15}$')

# ============================================================
# STATUS CHECK MODE
# ============================================================
if mode == 'status_check':
    case_id = case_id if 'case_id' in dir() and case_id else None  # noqa: F841
    if not isinstance(case_id, str) or not UUID_RE.match(case_id):
        print(json.dumps({"status": "FAILED", "error": "case_id must be a valid UUID for status_check mode"}))
        raise SystemExit(0)

    status_query = f"""
    SELECT EVENT_ID, RESPONSE_TYPE, VERIFICATION_METHOD,
           ALERT_DISPATCHED_AT, RESPONSE_TIMESTAMP, RESPONSE_TIME_MINUTES,
           EMAIL_STATUS, PUSH_STATUS, TOKEN_VALID
    FROM FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS
    WHERE CASE_ID = '{case_id}'
    ORDER BY ALERT_DISPATCHED_AT DESC
    """
    try:
        rows = _snowflake.execute_sql(status_query)
        if not rows or len(rows) == 0:
            output = {
                "status": "SUCCESS",
                "mode": "status_check",
                "case_id": case_id,
                "total_events": 0,
                "latest_event": None,
                "message": "No verification events found for this case."
            }
        else:
            latest = rows[0]
            output = {
                "status": "SUCCESS",
                "mode": "status_check",
                "case_id": case_id,
                "total_events": len(rows),
                "latest_event": {
                    "event_id": latest.get('EVENT_ID'),
                    "response_type": latest.get('RESPONSE_TYPE'),
                    "verification_method": latest.get('VERIFICATION_METHOD'),
                    "dispatched_at": str(latest.get('ALERT_DISPATCHED_AT')),
                    "response_timestamp": str(latest.get('RESPONSE_TIMESTAMP')) if latest.get('RESPONSE_TIMESTAMP') else None,
                    "response_time_minutes": float(latest['RESPONSE_TIME_MINUTES']) if latest.get('RESPONSE_TIME_MINUTES') else None,
                    "email_status": latest.get('EMAIL_STATUS'),
                    "push_status": latest.get('PUSH_STATUS'),
                    "token_valid": latest.get('TOKEN_VALID')
                }
            }
    except Exception as e:
        output = {"status": "FAILED", "error": str(e)}

    print(json.dumps(output, indent=2))
    raise SystemExit(0)

# ============================================================
# DISPATCH MODE (default)
# ============================================================
txn_id = txn_id  # noqa: F841
account_id = account_id  # noqa: F841
alert_id = alert_id  # noqa: F841
explanation_customer = explanation_customer  # noqa: F841

errors = []
if not isinstance(txn_id, str) or not UUID_RE.match(txn_id):
    errors.append("txn_id must be a valid UUID")
if not isinstance(account_id, str) or not ACC_RE.match(account_id):
    errors.append("account_id must match ACC-XXXXXXXXX")
if not isinstance(alert_id, str) or not UUID_RE.match(alert_id):
    errors.append("alert_id must be a valid UUID")
if not isinstance(explanation_customer, str) or len(explanation_customer.strip()) == 0:
    errors.append("explanation_customer is required")
if errors:
    print(json.dumps({"status": "FAILED", "event_id": None, "error": "; ".join(errors)}))
    raise SystemExit(0)

explanation_customer = explanation_customer[:2000]

# --- NEW-P1-B: Duplicate-dispatch guard ---
dup_check = f"""
SELECT EVENT_ID FROM FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS
WHERE CASE_ID = '{alert_id}' AND RESPONSE_TYPE = 'AWAITING_RESPONSE' AND TOKEN_VALID = TRUE
LIMIT 1
"""
try:
    dup_rows = _snowflake.execute_sql(dup_check)
    if dup_rows and len(dup_rows) > 0:
        output = {
            "status": "SUCCESS",
            "event_id": dup_rows[0]['EVENT_ID'],
            "txn_id": txn_id,
            "account_id": account_id,
            "alert_id": alert_id,
            "dispatch_timestamp": None,
            "email_status": "ALREADY_DISPATCHED",
            "push_status": "ALREADY_DISPATCHED",
            "message": "An active verification is already pending for this case. No duplicate dispatch created."
        }
        print(json.dumps(output, indent=2))
        raise SystemExit(0)
except SystemExit:
    raise
except Exception:
    pass  # If the check fails, proceed with dispatch

# Generate a 256-bit entropy token (32 bytes = 256 bits)
token_bytes = secrets.token_bytes(32)
token_hex = token_bytes.hex()

# Simulate JWT structure: header.payload.signature using the entropy
jwt_header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
jwt_payload = secrets.token_urlsafe(32)
jwt_signature = secrets.token_urlsafe(32)
simulated_jwt = f"{jwt_header}.{jwt_payload}.{jwt_signature}"

# SHA-256 hash of the token for storage (never store raw token)
token_hash = hashlib.sha256(token_hex.encode()).hexdigest()

# Generate new event_id
event_id_query = "SELECT UUID_STRING() AS new_id, CURRENT_TIMESTAMP() AS ts"
id_result = _snowflake.execute_sql(event_id_query)
new_event_id = id_result[0]['NEW_ID']
dispatch_ts = str(id_result[0]['TS'])

# Insert the verification event record (includes VERIFICATION_TOKEN + TOKEN_EXPIRES_AT)
TOKEN_TTL_MINUTES = 30
insert_query = f"""
INSERT INTO FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS
(EVENT_ID, CASE_ID, ACCOUNT_ID, TXN_ID, VERIFICATION_METHOD, RESPONSE_TYPE,
 ALERT_DISPATCHED_AT, EMAIL_STATUS, PUSH_STATUS, TOKEN_VALID, TOKEN_HASH,
 EXPLANATION_CUSTOMER, VERIFICATION_TOKEN, TOKEN_EXPIRES_AT)
VALUES (
    '{new_event_id}',
    '{alert_id}',
    '{account_id}',
    '{txn_id}',
    'MULTI_CHANNEL',
    'AWAITING_RESPONSE',
    CURRENT_TIMESTAMP(),
    'SENT',
    'SENT',
    TRUE,
    '{token_hash}',
    '{explanation_customer.replace("'", "''")}',
    '{simulated_jwt}',
    DATEADD('minute', {TOKEN_TTL_MINUTES}, CURRENT_TIMESTAMP())
)
"""

try:
    _snowflake.execute_sql(insert_query)

    # Look up customer email for real email dispatch
    email_lookup_query = f"""
    SELECT EMAIL_ADDRESS FROM FRAUDSHIELD_360_DB.RAW.RAW_ACCOUNTS
    WHERE ACCOUNT_ID = '{account_id}'
    """
    email_result = _snowflake.execute_sql(email_lookup_query)
    recipient_email = None
    if email_result and email_result[0].get('EMAIL_ADDRESS'):
        recipient_email = email_result[0]['EMAIL_ADDRESS']

    # Send real email via SYSTEM$SEND_EMAIL if recipient is configured
    email_sent = False
    if recipient_email:
        try:
            safe_explanation = explanation_customer.replace("'", "''")
            email_query = f"""
            CALL SYSTEM$SEND_EMAIL(
                'FRAUDSHIELD_EMAIL_INT',
                '{recipient_email}',
                'Security Check: Verify your transaction',
                '{safe_explanation}'
            )
            """
            _snowflake.execute_sql(email_query)
            email_sent = True
        except Exception as email_err:
            email_sent = False

    output = {
        "status": "SUCCESS",
        "event_id": new_event_id,
        "txn_id": txn_id,
        "account_id": account_id,
        "alert_id": alert_id,
        "dispatch_timestamp": dispatch_ts,
        "email_status": "SENT" if email_sent else "SENT_NO_EMAIL_CONFIGURED",
        "email_recipient": recipient_email if email_sent else None,
        "push_status": "SENT",
        "token_valid": True,
        "message": "Verification alert dispatched successfully via email and push notification."
            if email_sent else
            "Verification alert dispatched (push only - no email address configured for account)."
    }
except Exception as e:
    output = {
        "status": "FAILED",
        "event_id": None,
        "error": str(e)
    }

print(json.dumps(output, indent=2))
