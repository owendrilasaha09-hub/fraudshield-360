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

### Execution

Run the following SQL query using the `sql_execute` tool. Replace `{account_id}` and `{timeframe_hours}` with the actual parameter values:

```sql
WITH txn_window AS (
    SELECT *
    FROM FRAUDSHIELD_360_DB.CURATED.TRANSACTION_ENRICHED
    WHERE ACCOUNT_ID = '{account_id}'
      AND TXN_TIMESTAMP >= DATEADD(HOUR, -{timeframe_hours}, CURRENT_TIMESTAMP())
),
aggregated AS (
    SELECT
        MAX(RISK_SCORE) AS max_risk_score,
        MAX(RISK_TIER) AS max_risk_tier,
        ARRAY_AGG(DISTINCT CASE WHEN SIGNAL_VELOCITY THEN 'signal_velocity' END) AS vel,
        ARRAY_AGG(DISTINCT CASE WHEN SIGNAL_AMOUNT_ANOMALY THEN 'signal_amount_anomaly' END) AS amt,
        ARRAY_AGG(DISTINCT CASE WHEN SIGNAL_GEO_MISMATCH THEN 'signal_geo_mismatch' END) AS geo,
        ARRAY_AGG(DISTINCT CASE WHEN SIGNAL_WATCHLIST_MATCH THEN 'signal_watchlist_match' END) AS wl,
        ARRAY_AGG(DISTINCT CASE WHEN SIGNAL_ROUND_NUMBER THEN 'signal_round_number' END) AS rnd,
        ARRAY_AGG(DISTINCT CASE WHEN SIGNAL_STRUCTURING THEN 'signal_structuring' END) AS str,
        COUNT(*) AS txn_count
    FROM txn_window
)
SELECT
    COALESCE(max_risk_score, 0) AS risk_score,
    COALESCE(max_risk_tier, 'LOW') AS risk_tier,
    txn_count,
    ARRAY_COMPACT(ARRAY_CAT(ARRAY_CAT(ARRAY_CAT(vel, amt), ARRAY_CAT(geo, wl)), ARRAY_CAT(rnd, str))) AS triggered_signals
FROM aggregated
```

If no account_id is specified but the user asks a general question like "is there any fraud", run this population-level scan instead:

```sql
SELECT ACCOUNT_ID, RISK_SCORE, RISK_TIER, TXN_ID, AMOUNT, MERCHANT, GEO_COUNTRY,
       SIGNAL_VELOCITY, SIGNAL_AMOUNT_ANOMALY, SIGNAL_GEO_MISMATCH,
       SIGNAL_WATCHLIST_MATCH, SIGNAL_ROUND_NUMBER, SIGNAL_STRUCTURING,
       SIGNAL_EXPLANATION_ADMIN, TXN_TIMESTAMP
FROM FRAUDSHIELD_360_DB.CURATED.TRANSACTION_ENRICHED
WHERE RISK_SCORE > 0
  AND TXN_TIMESTAMP >= DATEADD(HOUR, -{timeframe_hours}, CURRENT_TIMESTAMP())
ORDER BY RISK_SCORE DESC
LIMIT 20
```

If the TRANSACTION_ENRICHED table has no data, also check FRAUD_ALERTS:

```sql
SELECT CASE_ID, ACCOUNT_ID, TXN_ID, ALERT_TYPE, RISK_SCORE, RISK_TIER,
       CASE_STATUS, ALERT_TIMESTAMP, ASSIGNED_ANALYST
FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
WHERE ALERT_TIMESTAMP >= DATEADD(DAY, -7, CURRENT_TIMESTAMP())
ORDER BY RISK_SCORE DESC
LIMIT 20
```

Interpret the results according to the signal weights: Velocity(15), Amount Anomaly(25), Geo Mismatch(20), Watchlist(30), Round Number(5), Structuring(20). Score thresholds: CRITICAL>=75, HIGH>=50, MEDIUM>=25, LOW<25.
