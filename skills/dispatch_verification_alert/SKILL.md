# dispatch_verification_alert

## name
dispatch_verification_alert

## description
Dispatches a customer verification alert for a flagged transaction, or checks the status of an existing verification. In dispatch mode, generates a 256-bit entropy JWT token, inserts a new verification event record, and confirms dispatch via JSON payload. In status_check mode, queries existing verification events for a case and returns the current status.

## instructions

You are a verification dispatch skill. When invoked, execute the `dispatch_verification_alert.py` script to either dispatch a new verification alert or check the status of an existing one.

### Parameters

- **mode** (VARCHAR, optional, default: "dispatch"): Either "dispatch" to send a new alert, or "status_check" to query existing verification status.

#### Dispatch mode parameters (mode = "dispatch"):
- **txn_id** (VARCHAR, required): The transaction ID that triggered the alert.
- **account_id** (VARCHAR, required): The account ID of the customer to alert.
- **alert_id** (VARCHAR, required): The fraud alert/case ID associated with this dispatch.
- **explanation_customer** (TEXT, required): The plain-language explanation to include in the customer notification.

#### Status check mode parameters (mode = "status_check"):
- **case_id** (VARCHAR, required): The fraud case ID to check verification status for.

### Behavior — Dispatch Mode

1. Generate a cryptographically secure 256-bit entropy token (simulated JWT).
2. Create a new EVENT_ID (UUID).
3. Insert a new record into `FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS`.
4. Return a JSON payload confirming success.

### Behavior — Status Check Mode

1. Query `FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS` for events matching the case_id.
2. Return the most recent verification event's status, method, timestamps, and channel statuses.
3. If no events exist, return a "no verification found" response.

### Output Schema — Dispatch Mode (JSON)

```json
{
  "status": "SUCCESS",
  "event_id": "<new UUID>",
  "txn_id": "<txn_id>",
  "account_id": "<account_id>",
  "alert_id": "<alert_id>",
  "dispatch_timestamp": "<ISO timestamp>",
  "email_status": "SENT",
  "push_status": "SENT",
  "token_valid": true,
  "token_hash": "<SHA-256 hash of 256-bit token>",
  "message": "Verification alert dispatched successfully via email and push notification."
}
```

### Output Schema — Status Check Mode (JSON)

```json
{
  "status": "SUCCESS",
  "mode": "status_check",
  "case_id": "<case_id>",
  "total_events": <integer>,
  "latest_event": {
    "event_id": "<UUID>",
    "response_type": "<AWAITING_RESPONSE|USER_CONFIRMED|USER_REQUESTED_REVIEW|USER_REJECTED|VERIFICATION_TIMEOUT>",
    "verification_method": "<method>",
    "dispatched_at": "<timestamp>",
    "response_timestamp": "<timestamp or null>",
    "response_time_minutes": <float or null>,
    "email_status": "<status>",
    "push_status": "<status>",
    "token_valid": <boolean>
  }
}
```

### Error Handling

If an operation fails, return:
```json
{
  "status": "FAILED",
  "event_id": null,
  "error": "<error message>"
}
```

### Execution

**Status Check Mode** — Run this SQL using the `sql_execute` tool:

```sql
SELECT EVENT_ID, RESPONSE_TYPE, VERIFICATION_METHOD,
       ALERT_DISPATCHED_AT, RESPONSE_TIMESTAMP, RESPONSE_TIME_MINUTES,
       EMAIL_STATUS, PUSH_STATUS, TOKEN_VALID
FROM FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS
WHERE CASE_ID = '{case_id}'
ORDER BY ALERT_DISPATCHED_AT DESC
```

**Dispatch Mode** — This requires inserting a record. Only proceed if the user explicitly requests dispatching a verification alert. Run this SQL:

```sql
INSERT INTO FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS
(EVENT_ID, CASE_ID, ACCOUNT_ID, TXN_ID, VERIFICATION_METHOD, RESPONSE_TYPE,
 ALERT_DISPATCHED_AT, EMAIL_STATUS, PUSH_STATUS, TOKEN_VALID, TOKEN_HASH,
 EXPLANATION_CUSTOMER)
VALUES (
    UUID_STRING(), '{alert_id}', '{account_id}', '{txn_id}',
    'MULTI_CHANNEL', 'AWAITING_RESPONSE', CURRENT_TIMESTAMP(),
    'SENT', 'SENT', TRUE, SHA2(UUID_STRING()),
    '{explanation_customer}'
)
```
