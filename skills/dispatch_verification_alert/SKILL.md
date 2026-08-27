# dispatch_verification_alert

## name
dispatch_verification_alert

## description
Dispatches a customer verification alert for a flagged transaction. Generates a 256-bit entropy JWT token, inserts a new verification event record, and confirms dispatch via JSON payload. Used when the fraud detection system needs to prompt a customer to confirm or deny a suspicious transaction.

## instructions

You are a verification dispatch skill. When invoked, execute the `dispatch_verification_alert.py` script to send a verification alert to the customer and record the event.

### Parameters

- **txn_id** (VARCHAR, required): The transaction ID that triggered the alert.
- **account_id** (VARCHAR, required): The account ID of the customer to alert.
- **alert_id** (VARCHAR, required): The fraud alert/case ID associated with this dispatch.
- **explanation_customer** (TEXT, required): The plain-language explanation to include in the customer notification.

### Behavior

1. Generate a cryptographically secure 256-bit entropy token (simulated JWT).
2. Create a new EVENT_ID (UUID).
3. Insert a new record into `FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS` with:
   - EVENT_ID: newly generated UUID
   - CASE_ID: the alert_id parameter
   - ACCOUNT_ID: the account_id parameter
   - TXN_ID: the txn_id parameter
   - VERIFICATION_METHOD: 'MULTI_CHANNEL' (both email and push)
   - RESPONSE_TYPE: 'AWAITING_RESPONSE'
   - ALERT_DISPATCHED_AT: CURRENT_TIMESTAMP()
   - EMAIL_STATUS: 'SENT'
   - PUSH_STATUS: 'SENT'
   - TOKEN_VALID: TRUE
   - TOKEN_HASH: SHA-256 hash of the generated token
   - EXPLANATION_CUSTOMER: the explanation text
4. Return a JSON payload confirming success.

### Output Schema (JSON)

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

### Error Handling

If the insert fails, return:
```json
{
  "status": "FAILED",
  "event_id": null,
  "error": "<error message>"
}
```

### Script

Execute the file `dispatch_verification_alert.py` located in this skill folder.
