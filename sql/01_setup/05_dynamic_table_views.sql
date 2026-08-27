-- ============================================================================
-- FraudShield 360 - Dynamic Table & Analytics Views
-- ============================================================================

USE DATABASE FRAUDSHIELD_360_DB;

-- Dynamic Table: TRANSACTION_ENRICHED
CREATE OR REPLACE DYNAMIC TABLE CURATED.TRANSACTION_ENRICHED
  TARGET_LAG = '5 minutes'
  WAREHOUSE = COMPUTE_WH
AS
WITH base AS (
    SELECT
        t.*,
        CASE WHEN COUNT(*) OVER (
            PARTITION BY t.ACCOUNT_ID
            ORDER BY t.TXN_TIMESTAMP
            RANGE BETWEEN INTERVAL '1 HOUR' PRECEDING AND CURRENT ROW
        ) > 3 THEN TRUE ELSE FALSE END AS signal_velocity,
        CASE WHEN t.AMOUNT > 5 * MEDIAN(t.AMOUNT) OVER (PARTITION BY t.ACCOUNT_ID)
            THEN TRUE ELSE FALSE END AS signal_amount_anomaly,
        CASE WHEN t.GEO_COUNTRY != COALESCE(a.DOMICILE_COUNTRY, t.GEO_COUNTRY)
            THEN TRUE ELSE FALSE END AS signal_geo_mismatch,
        CASE WHEN w.ENTITY_NAME IS NOT NULL
            THEN TRUE ELSE FALSE END AS signal_watchlist_match,
        CASE WHEN MOD(t.AMOUNT, 1000) = 0 AND t.AMOUNT >= 1000
            THEN TRUE ELSE FALSE END AS signal_round_number,
        CASE WHEN t.AMOUNT BETWEEN 9000 AND 9999
            THEN TRUE ELSE FALSE END AS signal_structuring
    FROM RAW.RAW_TRANSACTIONS t
    LEFT JOIN RAW.RAW_ACCOUNTS a ON t.ACCOUNT_ID = a.ACCOUNT_ID
    LEFT JOIN (SELECT DISTINCT ENTITY_NAME FROM RAW.RAW_WATCHLIST) w
        ON CONTAINS(UPPER(t.MERCHANT), UPPER(SPLIT_PART(w.ENTITY_NAME, ' ', 1)))
        AND LENGTH(SPLIT_PART(w.ENTITY_NAME, ' ', 1)) > 3
),
scored AS (
    SELECT *,
        LEAST(100,
            (signal_velocity::INT * 15) +
            (signal_amount_anomaly::INT * 25) +
            (signal_geo_mismatch::INT * 20) +
            (signal_watchlist_match::INT * 30) +
            (signal_round_number::INT * 5) +
            (signal_structuring::INT * 20)
        ) AS risk_score
    FROM base
)
SELECT
    TXN_ID, ACCOUNT_ID, AMOUNT, MERCHANT, GEO_COUNTRY, GEO_CITY, CHANNEL, TXN_TIMESTAMP, DEVICE_ID,
    signal_velocity, signal_amount_anomaly, signal_geo_mismatch,
    signal_watchlist_match, signal_round_number, signal_structuring,
    risk_score,
    CASE
        WHEN risk_score >= 75 THEN 'CRITICAL'
        WHEN risk_score >= 50 THEN 'HIGH'
        WHEN risk_score >= 25 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS risk_tier,
    CONCAT(
        'Signals fired: ',
        IFF(signal_velocity, 'VELOCITY ', ''),
        IFF(signal_amount_anomaly, 'AMOUNT_ANOMALY ', ''),
        IFF(signal_geo_mismatch, 'GEO_MISMATCH ', ''),
        IFF(signal_watchlist_match, 'WATCHLIST_HIT ', ''),
        IFF(signal_round_number, 'ROUND_NUMBER ', ''),
        IFF(signal_structuring, 'STRUCTURING ', ''),
        '| Score: ', risk_score::VARCHAR,
        ' | Account: ', ACCOUNT_ID,
        ' | Geo: ', GEO_COUNTRY,
        ' | Amount: $', AMOUNT::VARCHAR
    ) AS signal_explanation_admin,
    CASE
        WHEN risk_score >= 75 THEN 'This transaction was flagged due to multiple unusual indicators.'
        WHEN risk_score >= 50 THEN 'We noticed some unusual activity on this transaction.'
        WHEN risk_score >= 25 THEN 'This transaction had a minor flag due to a slight deviation from your usual patterns.'
        ELSE 'This transaction appears consistent with your normal account activity.'
    END AS signal_explanation_customer
FROM scored;

-- Analytics Views
CREATE OR REPLACE VIEW ANALYTICS.V_VERIFICATION_METRICS AS
WITH base AS (
    SELECT cve.RESPONSE_TYPE, cve.RESPONSE_TIME_MINUTES
    FROM AGENTS.CUSTOMER_VERIFICATION_EVENTS cve
    INNER JOIN AGENTS.FRAUD_ALERTS fa ON cve.CASE_ID = fa.CASE_ID
    WHERE cve.RESPONSE_TYPE IS NOT NULL
)
SELECT
    COUNT(*) AS total_verifications_sent,
    COUNT(CASE WHEN RESPONSE_TYPE = 'USER_CONFIRMED' THEN 1 END) AS confirmed_count,
    COUNT(CASE WHEN RESPONSE_TYPE = 'USER_REQUESTED_REVIEW' THEN 1 END) AS review_count,
    COUNT(CASE WHEN RESPONSE_TYPE = 'USER_REJECTED' THEN 1 END) AS rejected_count,
    COUNT(CASE WHEN RESPONSE_TYPE = 'VERIFICATION_TIMEOUT' THEN 1 END) AS timeout_count,
    ROUND(confirmed_count * 100.0 / NULLIF(total_verifications_sent, 0), 2) AS acceptance_rate_pct,
    ROUND(review_count * 100.0 / NULLIF(total_verifications_sent, 0), 2) AS hold_rate_pct,
    ROUND(rejected_count * 100.0 / NULLIF(total_verifications_sent, 0), 2) AS rejection_rate_pct,
    ROUND(timeout_count * 100.0 / NULLIF(total_verifications_sent, 0), 2) AS timeout_rate_pct,
    ROUND(AVG(CASE WHEN RESPONSE_TYPE != 'VERIFICATION_TIMEOUT' THEN RESPONSE_TIME_MINUTES END), 2) AS avg_response_time_minutes_excl_timeouts
FROM base;

CREATE OR REPLACE VIEW ANALYTICS.V_FRAUD_RISK_DASHBOARD AS
SELECT
    DATE_TRUNC('DAY', TXN_TIMESTAMP) AS metric_date,
    COUNT(*) AS total_transactions,
    COUNT(CASE WHEN RISK_SCORE > 0 THEN 1 END) AS flagged_transactions,
    ROUND(flagged_transactions * 100.0 / NULLIF(total_transactions, 0), 2) AS flag_rate_pct,
    AVG(RISK_SCORE) AS avg_risk_score,
    SUM(CASE WHEN RISK_TIER IN ('HIGH','CRITICAL') THEN AMOUNT ELSE 0 END) AS high_risk_volume
FROM CURATED.TRANSACTION_ENRICHED
GROUP BY metric_date;
