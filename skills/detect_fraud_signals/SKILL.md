# detect_fraud_signals

## name
detect_fraud_signals

## description
Detects fraud signals for a given account within a specified timeframe. Queries enriched transaction data and returns a JSON payload with risk score, risk tier, triggered signals, explanations for both admin and customer audiences, and whether verification is required.

## instructions

You are a fraud detection skill. When invoked, execute the `detect_fraud_signals.py` script to analyze transactions for a specific account.

### Parameters

- **account_id** (VARCHAR, required): The account identifier to analyze (e.g., 'ACC-000000000123').
- **timeframe_hours** (INTEGER, optional, default: 24): How many hours back from the current time to analyze transactions.

### Behavior

1. Query `FRAUDSHIELD_360_DB.CURATED.TRANSACTION_ENRICHED` for the given account within the timeframe.
2. Aggregate all triggered signals across the transactions found.
3. Compute the maximum risk score and corresponding risk tier.
4. Generate an admin explanation that references specific signal IDs and thresholds.
5. Generate a customer explanation written at a 10th-grade reading level, avoiding technical jargon.
6. Set `verification_required` to TRUE if risk_tier is HIGH or CRITICAL.

### Output Schema (JSON)

```json
{
  "risk_score": <integer 0-100>,
  "risk_tier": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "triggered_signals": ["<signal_name>", ...],
  "explanation_admin": "<technical explanation with signal IDs and thresholds>",
  "explanation_customer": "<plain-language explanation for customer alert>",
  "verification_required": <true|false>
}
```

### Example Invocation

"Check fraud signals for account ACC-000000000042 over the last 48 hours."

Run the script with:
- account_id = "ACC-000000000042"
- timeframe_hours = 48

### Script

Execute the file `detect_fraud_signals.py` located in this skill folder.
