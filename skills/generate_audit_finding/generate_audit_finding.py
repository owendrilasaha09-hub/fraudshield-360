import json
import _snowflake
from datetime import datetime

# Parameter injected by skill runtime
case_id = case_id  # noqa: F841

# Fetch all data in a single joined query
query = f"""
WITH alert_data AS (
    SELECT
        fa.CASE_ID,
        fa.ACCOUNT_ID,
        fa.TXN_ID,
        fa.ALERT_TIMESTAMP,
        fa.ALERT_TYPE,
        fa.RISK_SCORE AS ALERT_RISK_SCORE,
        fa.RISK_TIER AS ALERT_RISK_TIER,
        fa.TRIGGERED_SIGNALS,
        fa.ASSIGNED_ANALYST,
        fa.CASE_STATUS
    FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS fa
    WHERE fa.CASE_ID = '{case_id}'
),
txn_data AS (
    SELECT
        te.TXN_ID,
        te.ACCOUNT_ID,
        te.AMOUNT,
        te.MERCHANT,
        te.GEO_COUNTRY,
        te.GEO_CITY,
        te.CHANNEL,
        te.TXN_TIMESTAMP,
        te.DEVICE_ID,
        te.SIGNAL_VELOCITY,
        te.SIGNAL_AMOUNT_ANOMALY,
        te.SIGNAL_GEO_MISMATCH,
        te.SIGNAL_WATCHLIST_MATCH,
        te.SIGNAL_ROUND_NUMBER,
        te.SIGNAL_STRUCTURING,
        te.RISK_SCORE,
        te.RISK_TIER,
        te.SIGNAL_EXPLANATION_ADMIN,
        te.SIGNAL_EXPLANATION_CUSTOMER
    FROM FRAUDSHIELD_360_DB.CURATED.TRANSACTION_ENRICHED te
    INNER JOIN alert_data ad ON te.TXN_ID = ad.TXN_ID
),
verification_data AS (
    SELECT
        cve.EVENT_ID,
        cve.CASE_ID,
        cve.VERIFICATION_METHOD,
        cve.RESPONSE_TYPE,
        cve.RESPONSE_TIMESTAMP,
        cve.RESPONSE_TIME_MINUTES,
        cve.DEVICE_FINGERPRINT,
        cve.IP_ADDRESS
    FROM FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS cve
    INNER JOIN alert_data ad ON cve.CASE_ID = ad.CASE_ID
),
account_data AS (
    SELECT
        ra.ACCOUNT_ID,
        ra.ACCOUNT_TYPE,
        ra.DOMICILE_COUNTRY,
        ra.ONBOARDING_DATE,
        ra.KYC_STATUS,
        ra.RISK_TIER
    FROM FRAUDSHIELD_360_DB.RAW.RAW_ACCOUNTS ra
    INNER JOIN alert_data ad ON ra.ACCOUNT_ID = ad.ACCOUNT_ID
),
history AS (
    SELECT COUNT(*) AS total_alerts
    FROM FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS
    WHERE ACCOUNT_ID = (SELECT ACCOUNT_ID FROM alert_data)
)
SELECT
    ad.CASE_ID,
    ad.ACCOUNT_ID,
    ad.TXN_ID,
    ad.ALERT_TIMESTAMP,
    ad.ALERT_TYPE,
    ad.ALERT_RISK_SCORE,
    ad.ALERT_RISK_TIER,
    ad.TRIGGERED_SIGNALS,
    ad.ASSIGNED_ANALYST,
    ad.CASE_STATUS,
    td.AMOUNT,
    td.MERCHANT,
    td.GEO_COUNTRY,
    td.GEO_CITY,
    td.CHANNEL,
    td.TXN_TIMESTAMP,
    td.DEVICE_ID,
    td.SIGNAL_VELOCITY,
    td.SIGNAL_AMOUNT_ANOMALY,
    td.SIGNAL_GEO_MISMATCH,
    td.SIGNAL_WATCHLIST_MATCH,
    td.SIGNAL_ROUND_NUMBER,
    td.SIGNAL_STRUCTURING,
    td.RISK_SCORE,
    td.RISK_TIER,
    td.SIGNAL_EXPLANATION_ADMIN,
    acct.ACCOUNT_TYPE,
    acct.DOMICILE_COUNTRY,
    acct.ONBOARDING_DATE,
    acct.KYC_STATUS,
    acct.RISK_TIER AS ACCOUNT_RISK_TIER,
    vd.VERIFICATION_METHOD,
    vd.RESPONSE_TYPE,
    vd.RESPONSE_TIMESTAMP,
    vd.RESPONSE_TIME_MINUTES,
    vd.DEVICE_FINGERPRINT,
    vd.IP_ADDRESS AS VERIFICATION_IP,
    h.total_alerts AS HISTORICAL_ALERT_COUNT
FROM alert_data ad
LEFT JOIN txn_data td ON ad.TXN_ID = td.TXN_ID
LEFT JOIN account_data acct ON ad.ACCOUNT_ID = acct.ACCOUNT_ID
LEFT JOIN verification_data vd ON ad.CASE_ID = vd.CASE_ID
CROSS JOIN history h
LIMIT 1
"""

result = _snowflake.execute_sql(query)

if not result or len(result) == 0:
    print(f"ERROR: No data found for case_id '{case_id}'. Verify the case exists in FRAUD_ALERTS.")
else:
    r = result[0]

    # Build signal descriptions
    signals_fired = []
    if r.get('SIGNAL_VELOCITY'):
        signals_fired.append("VELOCITY: More than 3 transactions detected within a 1-hour window (weight: 15)")
    if r.get('SIGNAL_AMOUNT_ANOMALY'):
        signals_fired.append("AMOUNT_ANOMALY: Transaction amount exceeds 5x the account median (weight: 25)")
    if r.get('SIGNAL_GEO_MISMATCH'):
        signals_fired.append("GEO_MISMATCH: Transaction country does not match account domicile (weight: 20)")
    if r.get('SIGNAL_WATCHLIST_MATCH'):
        signals_fired.append("WATCHLIST_MATCH: Merchant/counterparty matches a watchlist entity (weight: 30)")
    if r.get('SIGNAL_ROUND_NUMBER'):
        signals_fired.append("ROUND_NUMBER: Transaction amount is a round thousand (weight: 5)")
    if r.get('SIGNAL_STRUCTURING'):
        signals_fired.append("STRUCTURING: Amount in $9,000-$9,999 range, below reporting threshold (weight: 20)")

    signals_text = "\n".join([f"  - {s}" for s in signals_fired]) if signals_fired else "  - No signals triggered"

    # Verification response (CRITICAL for Section 4)
    response_type = r.get('RESPONSE_TYPE', 'NO_VERIFICATION_SENT')
    verification_method = r.get('VERIFICATION_METHOD', 'N/A')
    response_time = r.get('RESPONSE_TIME_MINUTES', 'N/A')
    device_fp = r.get('DEVICE_FINGERPRINT', 'N/A')
    verification_ip = r.get('VERIFICATION_IP', 'N/A')

    # Risk assessment
    risk_score = r.get('RISK_SCORE', 0)
    risk_tier = r.get('RISK_TIER', 'LOW')

    # Regulatory implications based on amount and signals
    amount = r.get('AMOUNT', 0)
    regulatory_notes = []
    if amount and amount >= 10000:
        regulatory_notes.append("Transaction exceeds $10,000 CTR threshold (31 CFR 1010.311)")
    if r.get('SIGNAL_STRUCTURING'):
        regulatory_notes.append("Potential structuring to avoid CTR filing (31 USC 5324)")
    if r.get('SIGNAL_GEO_MISMATCH'):
        regulatory_notes.append("Cross-border transaction may require enhanced due diligence (FATF Rec. 16)")
    if r.get('SIGNAL_WATCHLIST_MATCH'):
        regulatory_notes.append("Possible OFAC match requires immediate escalation (31 CFR Part 501)")
    if risk_tier in ('HIGH', 'CRITICAL'):
        regulatory_notes.append("SAR filing recommended within 30 days per BSA requirements (31 CFR 1020.320)")
    if not regulatory_notes:
        regulatory_notes.append("No immediate regulatory filing triggered. Continue monitoring.")

    # Recommended actions
    actions = []
    if risk_tier == 'CRITICAL':
        actions.append("IMMEDIATE: Freeze account pending investigation")
        actions.append("ESCALATE: Notify BSA Officer within 24 hours")
        actions.append("FILE: Prepare SAR within 30 calendar days")
    elif risk_tier == 'HIGH':
        actions.append("REVIEW: Assign to senior analyst for detailed investigation")
        actions.append("MONITOR: Place account on enhanced monitoring for 90 days")
        actions.append("CONSIDER: Evaluate need for SAR filing based on investigation outcome")
    else:
        actions.append("MONITOR: Continue standard transaction monitoring")
        actions.append("DOCUMENT: Log finding for periodic review")

    if response_type == 'USER_REJECTED':
        actions.append("PRIORITY: Customer denied transaction - initiate chargeback and credential reset")
    elif response_type == 'VERIFICATION_TIMEOUT':
        actions.append("FOLLOW-UP: Re-attempt customer verification via alternate channel")

    actions_text = "\n".join([f"  {i+1}. {a}" for i, a in enumerate(actions)])
    regulatory_text = "\n".join([f"  - {rn}" for rn in regulatory_notes])

    # Assemble the 8-section report
    report = f"""=== SUSPICIOUS ACTIVITY REPORT ===
Case ID: {r.get('CASE_ID', case_id)}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Assigned Analyst: {r.get('ASSIGNED_ANALYST', 'Unassigned')}
Case Status: {r.get('CASE_STATUS', 'UNKNOWN')}

--- SECTION 1: EXECUTIVE SUMMARY ---
Alert Type: {r.get('ALERT_TYPE', 'N/A')}
Risk Tier: {risk_tier} (Score: {risk_score}/100)
Account: {r.get('ACCOUNT_ID', 'N/A')}
Transaction Amount: ${amount:,.2f} via {r.get('CHANNEL', 'N/A')}
Recommendation: {'Immediate escalation and SAR filing required' if risk_tier == 'CRITICAL' else 'Further investigation recommended' if risk_tier == 'HIGH' else 'Standard monitoring, no immediate action required'}

--- SECTION 2: SUBJECT IDENTIFICATION ---
Account ID: {r.get('ACCOUNT_ID', 'N/A')}
Account Type: {r.get('ACCOUNT_TYPE', 'N/A')}
Domicile Country: {r.get('DOMICILE_COUNTRY', 'N/A')}
Onboarding Date: {r.get('ONBOARDING_DATE', 'N/A')}
KYC Status: {r.get('KYC_STATUS', 'N/A')}
Account Risk Tier: {r.get('ACCOUNT_RISK_TIER', 'N/A')}

--- SECTION 3: TRANSACTION DETAILS ---
Transaction ID: {r.get('TXN_ID', 'N/A')}
Timestamp: {r.get('TXN_TIMESTAMP', 'N/A')}
Amount: ${amount:,.2f}
Merchant: {r.get('MERCHANT', 'N/A')}
Channel: {r.get('CHANNEL', 'N/A')}
Geographic Location: {r.get('GEO_CITY', 'N/A')}, {r.get('GEO_COUNTRY', 'N/A')}
Device ID: {r.get('DEVICE_ID', 'N/A')[:40] if r.get('DEVICE_ID') else 'N/A'}...

--- SECTION 4: EVIDENCE CHAIN ---
Triggered Signals:
{signals_text}

Customer Verification Response:
  Status: ** {response_type} **
  Method: {verification_method}
  Response Time: {response_time} minutes
  Verification Device: {str(device_fp)[:40] if device_fp else 'N/A'}...
  Verification IP: {verification_ip}
  Response Timestamp: {r.get('RESPONSE_TIMESTAMP', 'N/A')}

--- SECTION 5: RISK ASSESSMENT ---
Composite Risk Score: {risk_score}/100
Risk Tier: {risk_tier}
Signal Weights Applied:
  - Velocity: 15 pts (fired: {r.get('SIGNAL_VELOCITY', False)})
  - Amount Anomaly: 25 pts (fired: {r.get('SIGNAL_AMOUNT_ANOMALY', False)})
  - Geo Mismatch: 20 pts (fired: {r.get('SIGNAL_GEO_MISMATCH', False)})
  - Watchlist Match: 30 pts (fired: {r.get('SIGNAL_WATCHLIST_MATCH', False)})
  - Round Number: 5 pts (fired: {r.get('SIGNAL_ROUND_NUMBER', False)})
  - Structuring: 20 pts (fired: {r.get('SIGNAL_STRUCTURING', False)})
Admin Explanation: {r.get('SIGNAL_EXPLANATION_ADMIN', 'N/A')}

--- SECTION 6: PATTERN ANALYSIS ---
Historical Alert Count (this account): {r.get('HISTORICAL_ALERT_COUNT', 0)}
Alert Type: {r.get('ALERT_TYPE', 'N/A')}
Behavioral Notes:
  - {'Repeat offender: multiple alerts on file' if r.get('HISTORICAL_ALERT_COUNT', 0) > 3 else 'Limited prior alert history'}
  - {'High-value transaction pattern detected' if amount and amount > 5000 else 'Transaction amount within normal range'}
  - {'Cross-border activity flagged' if r.get('SIGNAL_GEO_MISMATCH') else 'Domestic transaction'}

--- SECTION 7: REGULATORY IMPLICATIONS ---
{regulatory_text}

--- SECTION 8: RECOMMENDED ACTIONS ---
{actions_text}

=== END OF REPORT ==="""

    print(report)
