import json
import _snowflake

# Parameters passed by the agent
account_id = account_id  # noqa: F841 - injected by skill runtime
timeframe_hours = timeframe_hours if 'timeframe_hours' in dir() else 24  # noqa: F841

query = f"""
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
"""

result = _snowflake.execute_sql(query)
row = result[0] if result else None

if row is None or row['TXN_COUNT'] == 0:
    output = {
        "risk_score": 0,
        "risk_tier": "LOW",
        "triggered_signals": [],
        "explanation_admin": f"No transactions found for account {account_id} within the last {timeframe_hours} hours.",
        "explanation_customer": "We found no recent transactions to review for your account. Everything looks good.",
        "verification_required": False
    }
else:
    risk_score = row['RISK_SCORE']
    risk_tier = row['RISK_TIER']
    signals = row['TRIGGERED_SIGNALS'] if row['TRIGGERED_SIGNALS'] else []
    txn_count = row['TXN_COUNT']

    # Determine risk tier from score (in case MAX on string didn't yield correct ordering)
    if risk_score >= 75:
        risk_tier = "CRITICAL"
    elif risk_score >= 50:
        risk_tier = "HIGH"
    elif risk_score >= 25:
        risk_tier = "MEDIUM"
    else:
        risk_tier = "LOW"

    # Build admin explanation
    signal_details = []
    if 'signal_velocity' in signals:
        signal_details.append("VELOCITY (>3 txns/hour, weight=15)")
    if 'signal_amount_anomaly' in signals:
        signal_details.append("AMOUNT_ANOMALY (>5x median, weight=25)")
    if 'signal_geo_mismatch' in signals:
        signal_details.append("GEO_MISMATCH (country != domicile, weight=20)")
    if 'signal_watchlist_match' in signals:
        signal_details.append("WATCHLIST_MATCH (entity hit, weight=30)")
    if 'signal_round_number' in signals:
        signal_details.append("ROUND_NUMBER (mod 1000=0, weight=5)")
    if 'signal_structuring' in signals:
        signal_details.append("STRUCTURING ($9000-$9999 range, weight=20)")

    explanation_admin = (
        f"Account {account_id} | Timeframe: {timeframe_hours}h | "
        f"Transactions analyzed: {txn_count} | "
        f"Max composite score: {risk_score}/100 | "
        f"Tier: {risk_tier} | "
        f"Triggered signals: {'; '.join(signal_details) if signal_details else 'None'}"
    )

    # Build customer explanation
    if risk_tier == "CRITICAL":
        explanation_customer = (
            "We detected several unusual patterns on your account that require your immediate attention. "
            "These include transactions from unexpected locations, amounts that are much larger than your "
            "typical activity, and rapid back-to-back transactions. For your protection, we need you to "
            "confirm whether you authorized these transactions."
        )
    elif risk_tier == "HIGH":
        explanation_customer = (
            "We noticed some activity on your account that looks different from your usual spending. "
            "This could involve an unfamiliar location or a transaction amount that stands out. "
            "Please review your recent transactions and let us know if anything looks unfamiliar."
        )
    elif risk_tier == "MEDIUM":
        explanation_customer = (
            "One of your recent transactions had a minor flag. This can happen when a purchase is made "
            "in a new location or for an unusual amount. No action is needed unless you don't recognize "
            "the transaction."
        )
    else:
        explanation_customer = (
            "Your recent account activity appears normal. No unusual patterns were detected."
        )

    verification_required = risk_tier in ("HIGH", "CRITICAL")

    output = {
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "triggered_signals": signals,
        "explanation_admin": explanation_admin,
        "explanation_customer": explanation_customer,
        "verification_required": verification_required
    }

print(json.dumps(output, indent=2))
