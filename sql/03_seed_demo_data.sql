-- ============================================================================
-- FraudShield 360 — Demo Seed Data
-- Run AFTER 01_complete_setup.sql and 02_deploy_agent_apps.sql
-- Re-runnable: each section clears existing demo data before inserting
-- ============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE FRAUDSHIELD_360_DB;
USE WAREHOUSE COMPUTE_WH;

-- ============================================================================
-- 1. RAW_WATCHLIST — Sanctions/PEP entities for watchlist matching
-- ============================================================================
DELETE FROM RAW.RAW_WATCHLIST WHERE LIST_SOURCE IN ('OFAC_SDN','INTERPOL','EU_SANCTIONS','FATF_BLACKLIST');

INSERT INTO RAW.RAW_WATCHLIST (ENTITY_NAME, ENTITY_TYPE, LIST_SOURCE, JURISDICTION, DATE_ADDED, CONFIDENCE_SCORE) VALUES
('Darknet Exchange LLC',   'ORGANIZATION', 'OFAC_SDN',       'RU', '2025-03-15', 0.99),
('Petrokov Industries',    'ORGANIZATION', 'EU_SANCTIONS',   'RU', '2024-11-20', 0.97),
('Golden Shell Trading',   'ORGANIZATION', 'FATF_BLACKLIST', 'NG', '2025-06-01', 0.95),
('Ahmad Al-Rashid',        'INDIVIDUAL',   'OFAC_SDN',       'IR', '2024-08-10', 0.98),
('NovaCash Financial',     'ORGANIZATION', 'INTERPOL',       'PA', '2025-01-22', 0.93),
('Meridian Hawala Network', 'ORGANIZATION', 'FATF_BLACKLIST', 'AE', '2025-04-05', 0.96);

-- ============================================================================
-- 2. RAW_ACCOUNTS — 12 accounts across geographies and risk tiers
-- ============================================================================
DELETE FROM RAW.RAW_ACCOUNTS WHERE ACCOUNT_ID LIKE 'ACC-00000000000%';

INSERT INTO RAW.RAW_ACCOUNTS (ACCOUNT_ID, CUSTOMER_NAME_HASH, KYC_STATUS, RISK_TIER, ONBOARDING_DATE, ACCOUNT_TYPE, DOMICILE_COUNTRY, REGISTERED_EMAIL_HASH, REGISTERED_MOBILE_HASH, CUSTOMER_NAME, PHONE_NUMBER, EMAIL_ADDRESS) VALUES
('ACC-000000000001', SHA2('Alice Johnson'),   'VERIFIED',   'LOW',      '2023-06-15', 'PERSONAL', 'US', SHA2('alice@example.com'),  SHA2('+1-555-0101'), 'Alice Johnson',   '+1-555-0101', 'alice@example.com'),
('ACC-000000000002', SHA2('Bob Martinez'),     'VERIFIED',   'LOW',      '2023-09-20', 'PERSONAL', 'US', SHA2('bob@example.com'),    SHA2('+1-555-0102'), 'Bob Martinez',    '+1-555-0102', 'bob@example.com'),
('ACC-000000000003', SHA2('Charles Okafor'),   'VERIFIED',   'HIGH',     '2024-01-10', 'BUSINESS', 'NG', SHA2('charles@trade.ng'),   SHA2('+234-800-0001'), 'Charles Okafor', '+234-800-0001', 'charles@trade.ng'),
('ACC-000000000004', SHA2('Diana Chen'),       'VERIFIED',   'MEDIUM',   '2023-12-05', 'PERSONAL', 'US', SHA2('diana@example.com'),  SHA2('+1-555-0104'), 'Diana Chen',      '+1-555-0104', 'diana@example.com'),
('ACC-000000000005', SHA2('Erik Schneider'),   'VERIFIED',   'HIGH',     '2024-03-18', 'BUSINESS', 'DE', SHA2('erik@schneider.de'),  SHA2('+49-170-0001'), 'Erik Schneider',  '+49-170-0001', 'erik@schneider.de'),
('ACC-000000000006', SHA2('Fatima Al-Said'),   'VERIFIED',   'MEDIUM',   '2023-08-22', 'PERSONAL', 'AE', SHA2('fatima@mail.ae'),     SHA2('+971-50-0001'), 'Fatima Al-Said',  '+971-50-0001', 'fatima@mail.ae'),
('ACC-000000000007', SHA2('George Petrov'),    'PENDING',    'HIGH',     '2024-06-01', 'BUSINESS', 'RU', SHA2('george@petrov.ru'),   SHA2('+7-900-0001'), 'George Petrov',   '+7-900-0001', 'george@petrov.ru'),
('ACC-000000000008', SHA2('Hannah Williams'),  'VERIFIED',   'LOW',      '2022-11-15', 'PERSONAL', 'GB', SHA2('hannah@mail.co.uk'),  SHA2('+44-7700-0001'), 'Hannah Williams', '+44-7700-0001', 'hannah@mail.co.uk'),
('ACC-000000000009', SHA2('Igor Volkov'),      'EXPIRED',    'CRITICAL', '2024-02-28', 'BUSINESS', 'RU', SHA2('igor@volkov.ru'),     SHA2('+7-900-0002'), 'Igor Volkov',     '+7-900-0002', 'igor@volkov.ru'),
('ACC-000000000010', SHA2('Jennifer Park'),    'VERIFIED',   'MEDIUM',   '2023-07-10', 'PERSONAL', 'SG', SHA2('jen@mail.sg'),        SHA2('+65-9100-0001'), 'Jennifer Park',  '+65-9100-0001', 'jen@mail.sg'),
('ACC-000000000011', SHA2('Kevin DuBois'),     'VERIFIED',   'LOW',      '2023-04-01', 'PERSONAL', 'GB', SHA2('kevin@mail.co.uk'),   SHA2('+44-7700-0002'), 'Kevin DuBois',   '+44-7700-0002', 'kevin@mail.co.uk'),
('ACC-000000000012', SHA2('Lila Gupta'),       'UNDER_REVIEW','MEDIUM',  '2024-05-15', 'BUSINESS', 'SG', SHA2('lila@gupta.sg'),      SHA2('+65-9100-0002'), 'Lila Gupta',     '+65-9100-0002', 'lila@gupta.sg');

-- ============================================================================
-- 3. RAW_TRANSACTIONS — 51 transactions triggering all 6 DT fraud signals
-- ============================================================================
DELETE FROM RAW.RAW_TRANSACTIONS WHERE ACCOUNT_ID LIKE 'ACC-00000000000%';

INSERT INTO RAW.RAW_TRANSACTIONS (TXN_ID, ACCOUNT_ID, AMOUNT, MERCHANT, GEO_COUNTRY, GEO_CITY, CHANNEL, TXN_TIMESTAMP, DEVICE_ID) VALUES
-- ACC-001 Alice: Normal low-risk activity
(UUID_STRING(), 'ACC-000000000001',   45.99, 'Starbucks',                  'US', 'Seattle',      'POS',    '2026-10-01 08:15:00 +0000', 'DEV-A1-IPHONE14'),
(UUID_STRING(), 'ACC-000000000001',  120.00, 'Amazon.com',                 'US', 'Seattle',      'ONLINE', '2026-10-01 12:30:00 +0000', 'DEV-A1-IPHONE14'),
(UUID_STRING(), 'ACC-000000000001',   89.50, 'Whole Foods',                'US', 'Seattle',      'POS',    '2026-10-02 17:45:00 +0000', 'DEV-A1-IPHONE14'),
(UUID_STRING(), 'ACC-000000000001',  250.00, 'United Airlines',            'US', 'Seattle',      'ONLINE', '2026-10-03 09:00:00 +0000', 'DEV-A1-IPHONE14'),

-- ACC-002 Bob: Legitimate high-value purchase (false positive scenario)
(UUID_STRING(), 'ACC-000000000002',   67.00, 'Home Depot',                 'US', 'Austin',       'POS',    '2026-10-01 10:00:00 +0000', 'DEV-B2-PIXEL7'),
(UUID_STRING(), 'ACC-000000000002', 9100.00, 'Luxury Motors',              'US', 'Austin',       'WIRE',   '2026-10-02 14:00:00 +0000', 'DEV-B2-PIXEL7'),
(UUID_STRING(), 'ACC-000000000002',   35.00, 'Chipotle',                   'US', 'Austin',       'POS',    '2026-10-03 12:00:00 +0000', 'DEV-B2-PIXEL7'),

-- ACC-003 Charles: Watchlist match + high-risk jurisdiction (NG)
(UUID_STRING(), 'ACC-000000000003',  500.00, 'Lagos Electronics',          'NG', 'Lagos',        'ONLINE', '2026-09-28 08:00:00 +0000', 'DEV-C3-SAMSUNG'),
(UUID_STRING(), 'ACC-000000000003', 2500.00, 'West Africa Shipping',       'NG', 'Lagos',        'WIRE',   '2026-09-29 10:00:00 +0000', 'DEV-C3-SAMSUNG'),
(UUID_STRING(), 'ACC-000000000003',12000.00, 'Golden Shell Exports',       'NG', 'Abuja',        'WIRE',   '2026-10-01 15:00:00 +0000', 'DEV-C3-SAMSUNG'),

-- ACC-004 Diana: Structuring pattern (multiple ~$9K transactions)
(UUID_STRING(), 'ACC-000000000004', 9400.00, 'Premium Cash Services',      'US', 'New York',     'WIRE',   '2026-10-02 09:00:00 +0000', 'DEV-D4-IPHONE15'),
(UUID_STRING(), 'ACC-000000000004', 9200.00, 'Premium Cash Services',      'US', 'New York',     'WIRE',   '2026-10-02 09:30:00 +0000', 'DEV-D4-IPHONE15'),
(UUID_STRING(), 'ACC-000000000004', 9600.00, 'Premium Cash Services',      'US', 'New York',     'WIRE',   '2026-10-02 10:00:00 +0000', 'DEV-D4-IPHONE15'),
(UUID_STRING(), 'ACC-000000000004', 9300.00, 'Premium Cash Services',      'US', 'New York',     'WIRE',   '2026-10-02 10:30:00 +0000', 'DEV-D4-IPHONE15'),
(UUID_STRING(), 'ACC-000000000004',   55.00, 'Uber',                       'US', 'New York',     'POS',    '2026-10-03 18:00:00 +0000', 'DEV-D4-IPHONE15'),

-- ACC-005 Erik: Geo-mismatch + watchlist (DE account, RU transactions)
(UUID_STRING(), 'ACC-000000000005',  300.00, 'Berlin Coffee Co',           'DE', 'Berlin',       'POS',    '2026-09-25 07:00:00 +0000', 'DEV-E5-HUAWEI'),
(UUID_STRING(), 'ACC-000000000005', 1200.00, 'Munich Tech GmbH',           'DE', 'Munich',       'ONLINE', '2026-09-27 11:00:00 +0000', 'DEV-E5-HUAWEI'),
(UUID_STRING(), 'ACC-000000000005', 9800.00, 'Darknet Market Supplies',    'RU', 'Moscow',       'WIRE',   '2026-10-01 03:00:00 +0000', 'DEV-E5-ANON01'),

-- ACC-006 Fatima: Geo-mismatch (AE account, RU transaction)
(UUID_STRING(), 'ACC-000000000006',  450.00, 'Dubai Mall',                 'AE', 'Dubai',        'POS',    '2026-09-26 14:00:00 +0000', 'DEV-F6-IPHONE14'),
(UUID_STRING(), 'ACC-000000000006', 3000.00, 'Moscow Trade Center',        'RU', 'Moscow',       'WIRE',   '2026-10-01 22:00:00 +0000', 'DEV-F6-IPHONE14'),

-- ACC-007 George: Velocity anomaly + watchlist + geo-mismatch (RU acct, PA txn)
(UUID_STRING(), 'ACC-000000000007',  200.00, 'Moscow Grocery',             'RU', 'Moscow',       'POS',    '2026-10-02 06:00:00 +0000', 'DEV-G7-ANDROID'),
(UUID_STRING(), 'ACC-000000000007',  150.00, 'Yandex Taxi',               'RU', 'Moscow',       'ONLINE', '2026-10-02 06:15:00 +0000', 'DEV-G7-ANDROID'),
(UUID_STRING(), 'ACC-000000000007',  350.00, 'Russia Post',               'RU', 'Moscow',       'ONLINE', '2026-10-02 06:30:00 +0000', 'DEV-G7-ANDROID'),
(UUID_STRING(), 'ACC-000000000007',  800.00, 'Moscow Electronics',         'RU', 'Moscow',       'POS',    '2026-10-02 06:45:00 +0000', 'DEV-G7-ANDROID'),
(UUID_STRING(), 'ACC-000000000007', 9200.00, 'NovaCash Express Payments',  'PA', 'Panama City',  'WIRE',   '2026-10-02 07:00:00 +0000', 'DEV-G7-ANON02'),

-- ACC-008 Hannah: Completely clean account — normal UK spending
(UUID_STRING(), 'ACC-000000000008',   32.50, 'Tesco Express',              'GB', 'London',       'POS',    '2026-10-01 08:00:00 +0000', 'DEV-H8-IPHONE13'),
(UUID_STRING(), 'ACC-000000000008',   15.99, 'Costa Coffee',               'GB', 'London',       'POS',    '2026-10-01 12:30:00 +0000', 'DEV-H8-IPHONE13'),
(UUID_STRING(), 'ACC-000000000008',  450.00, 'British Airways',            'GB', 'London',       'ONLINE', '2026-10-02 20:00:00 +0000', 'DEV-H8-IPHONE13'),
(UUID_STRING(), 'ACC-000000000008',   78.00, 'Marks & Spencer',            'GB', 'London',       'POS',    '2026-10-03 16:00:00 +0000', 'DEV-H8-IPHONE13'),

-- ACC-009 Igor: Sanctions violation (IR) + shell company (KY)
(UUID_STRING(), 'ACC-000000000009',  700.00, 'St Petersburg Supplies',     'RU', 'St Petersburg','WIRE',   '2026-09-28 09:00:00 +0000', 'DEV-I9-LAPTOP'),
(UUID_STRING(), 'ACC-000000000009', 5000.00, 'Tehran Electronics',         'IR', 'Tehran',       'WIRE',   '2026-10-01 04:00:00 +0000', 'DEV-I9-LAPTOP'),
(UUID_STRING(), 'ACC-000000000009', 9500.00, 'Petrokov Global Services',   'KY', 'George Town',  'WIRE',   '2026-10-02 11:00:00 +0000', 'DEV-I9-ANON03'),

-- ACC-010 Jennifer: Mixed — mostly clean with one high-value offshore
(UUID_STRING(), 'ACC-000000000010',   25.00, 'FairPrice',                  'SG', 'Singapore',    'POS',    '2026-10-01 07:00:00 +0000', 'DEV-J10-PIXEL6'),
(UUID_STRING(), 'ACC-000000000010',  180.00, 'Singapore Airlines',         'SG', 'Singapore',    'ONLINE', '2026-10-01 19:00:00 +0000', 'DEV-J10-PIXEL6'),
(UUID_STRING(), 'ACC-000000000010',10000.00, 'Cayman Investment Fund',     'KY', 'George Town',  'WIRE',   '2026-10-02 14:30:00 +0000', 'DEV-J10-PIXEL6'),

-- ACC-011 Kevin: Velocity spike (4+ txns in 1 hour) + geo-mismatch (GB->FR)
(UUID_STRING(), 'ACC-000000000011',   50.00, 'Pret A Manger',             'GB', 'London',       'POS',    '2026-10-02 08:00:00 +0000', 'DEV-K11-SAMSUNG'),
(UUID_STRING(), 'ACC-000000000011',  200.00, 'Harrods',                   'GB', 'London',       'POS',    '2026-10-02 08:10:00 +0000', 'DEV-K11-SAMSUNG'),
(UUID_STRING(), 'ACC-000000000011',  350.00, 'Selfridges',                'GB', 'London',       'POS',    '2026-10-02 08:25:00 +0000', 'DEV-K11-SAMSUNG'),
(UUID_STRING(), 'ACC-000000000011',  120.00, 'John Lewis',                'GB', 'London',       'POS',    '2026-10-02 08:40:00 +0000', 'DEV-K11-SAMSUNG'),
(UUID_STRING(), 'ACC-000000000011', 1800.00, 'Galeries Lafayette',        'FR', 'Paris',        'POS',    '2026-10-02 09:00:00 +0000', 'DEV-K11-ANON04'),

-- ACC-012 Lila: Round number pattern (SG)
(UUID_STRING(), 'ACC-000000000012', 1000.00, 'SG Corporate Services',     'SG', 'Singapore',    'WIRE',   '2026-10-02 10:00:00 +0000', 'DEV-L12-MACBOOK'),
(UUID_STRING(), 'ACC-000000000012', 2000.00, 'Asia Pacific Consulting',   'SG', 'Singapore',    'WIRE',   '2026-10-02 11:00:00 +0000', 'DEV-L12-MACBOOK'),
(UUID_STRING(), 'ACC-000000000012', 5000.00, 'Regional Trade Alliance',   'SG', 'Singapore',    'WIRE',   '2026-10-02 12:00:00 +0000', 'DEV-L12-MACBOOK'),
(UUID_STRING(), 'ACC-000000000012', 3000.00, 'Island Freight Corp',       'SG', 'Singapore',    'WIRE',   '2026-10-03 09:00:00 +0000', 'DEV-L12-MACBOOK'),
(UUID_STRING(), 'ACC-000000000012',   88.50, 'Marina Bay Sands Hotel',    'SG', 'Singapore',    'POS',    '2026-10-03 20:00:00 +0000', 'DEV-L12-MACBOOK');

-- Wait for Dynamic Table to process (~5 min target lag)
-- You can check: SELECT COUNT(*) FROM CURATED.TRANSACTION_ENRICHED;

-- ============================================================================
-- 4. FRAUD_ALERTS — 8 cases across all state machine states
-- ============================================================================
-- NOTE: TXN_IDs below are placeholders. After inserting transactions above,
-- run this query to get actual TXN_IDs, then update the VALUES below:
--   SELECT TXN_ID, ACCOUNT_ID, AMOUNT, MERCHANT FROM RAW.RAW_TRANSACTIONS
--   WHERE AMOUNT IN (12000, 9400, 9800, 9500, 9200, 5000, 9100, 3000) ORDER BY AMOUNT DESC;
-- For a quick demo, the CASE_ID is the primary key so these will work regardless.

DELETE FROM AGENTS.FRAUD_ALERTS WHERE CASE_ID LIKE 'CASE-2026-%';

INSERT INTO AGENTS.FRAUD_ALERTS (
  CASE_ID, ACCOUNT_ID, TXN_ID, ALERT_TIMESTAMP, ALERT_TYPE, RISK_SCORE, RISK_TIER,
  TRIGGERED_SIGNALS, ASSIGNED_ANALYST, CASE_STATUS, RESOLUTION_NOTES,
  CREATED_AT, RESOLVED_BY, RESOLVED_AT, ESCALATED_BY, ESCALATED_AT, ESCALATED_TO, SLA_DUE_AT
)
SELECT * FROM (
-- OPEN: Watchlist match, Golden Shell Exports
SELECT 'CASE-2026-0001'::VARCHAR, 'ACC-000000000003'::VARCHAR,
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Golden Shell Exports' LIMIT 1),
       '2026-09-25 14:30:00 +0000'::TIMESTAMP_TZ, 'WATCHLIST_MATCH'::VARCHAR, 92, 'CRITICAL'::VARCHAR,
       PARSE_JSON('["watchlist_match","high_risk_jurisdiction","amount_threshold"]')::ARRAY,
       NULL::VARCHAR, 'OPEN'::VARCHAR, NULL::VARCHAR,
       '2026-09-25 14:30:00 +0000'::TIMESTAMP_TZ, NULL::VARCHAR, NULL::TIMESTAMP_TZ,
       NULL::VARCHAR, NULL::TIMESTAMP_TZ, NULL::VARCHAR,
       '2026-09-26 14:30:00 +0000'::TIMESTAMP_TZ
UNION ALL
-- OPEN: Structuring pattern
SELECT 'CASE-2026-0002', 'ACC-000000000004',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Premium Cash Services' AND AMOUNT=9400 LIMIT 1),
       '2026-09-26 09:15:00 +0000'::TIMESTAMP_TZ, 'STRUCTURING', 78, 'HIGH',
       PARSE_JSON('["structuring_pattern","velocity_anomaly"]')::ARRAY,
       NULL, 'OPEN', NULL,
       '2026-09-26 09:15:00 +0000'::TIMESTAMP_TZ, NULL, NULL,
       NULL, NULL, NULL,
       '2026-09-27 09:15:00 +0000'::TIMESTAMP_TZ
UNION ALL
-- UNDER_REVIEW: Analyst investigating Darknet Market
SELECT 'CASE-2026-0003', 'ACC-000000000005',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Darknet Market Supplies' LIMIT 1),
       '2026-09-24 11:00:00 +0000'::TIMESTAMP_TZ, 'WATCHLIST_MATCH', 88, 'CRITICAL',
       PARSE_JSON('["watchlist_match","high_risk_jurisdiction","velocity_anomaly"]')::ARRAY,
       'analyst_chen', 'UNDER_REVIEW', NULL,
       '2026-09-24 11:00:00 +0000'::TIMESTAMP_TZ, NULL, NULL,
       NULL, NULL, NULL,
       '2026-09-25 11:00:00 +0000'::TIMESTAMP_TZ
UNION ALL
-- ESCALATED: Petrokov shell company
SELECT 'CASE-2026-0004', 'ACC-000000000009',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Petrokov Global Services' LIMIT 1),
       '2026-09-23 16:45:00 +0000'::TIMESTAMP_TZ, 'WATCHLIST_MATCH', 95, 'CRITICAL',
       PARSE_JSON('["watchlist_match","high_risk_jurisdiction","amount_threshold","velocity_anomaly"]')::ARRAY,
       'sr_analyst_williams', 'ESCALATED', NULL,
       '2026-09-23 16:45:00 +0000'::TIMESTAMP_TZ, NULL, NULL,
       'analyst_chen', '2026-09-24 10:00:00 +0000'::TIMESTAMP_TZ, 'COMPLIANCE_TEAM',
       '2026-09-24 16:45:00 +0000'::TIMESTAMP_TZ
UNION ALL
-- PENDING_SAR: NovaCash money laundering
SELECT 'CASE-2026-0005', 'ACC-000000000007',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='NovaCash Express Payments' LIMIT 1),
       '2026-09-20 10:00:00 +0000'::TIMESTAMP_TZ, 'VELOCITY_ANOMALY', 82, 'HIGH',
       PARSE_JSON('["velocity_anomaly","high_risk_jurisdiction","amount_threshold"]')::ARRAY,
       'compliance_officer_davis', 'PENDING_SAR', NULL,
       '2026-09-20 10:00:00 +0000'::TIMESTAMP_TZ, NULL, NULL,
       'analyst_chen', '2026-09-21 14:00:00 +0000'::TIMESTAMP_TZ, 'COMPLIANCE_TEAM',
       '2026-09-21 10:00:00 +0000'::TIMESTAMP_TZ
UNION ALL
-- SAR_FILED: Iran sanctions violation
SELECT 'CASE-2026-0006', 'ACC-000000000009',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Tehran Electronics' LIMIT 1),
       '2026-09-15 08:00:00 +0000'::TIMESTAMP_TZ, 'SANCTIONS_VIOLATION', 97, 'CRITICAL',
       PARSE_JSON('["watchlist_match","high_risk_jurisdiction","sanctions_violation"]')::ARRAY,
       'compliance_officer_davis', 'SAR_FILED',
       'SAR filed with FinCEN ref SAR-2026-09-0042. Account frozen pending investigation.',
       '2026-09-15 08:00:00 +0000'::TIMESTAMP_TZ, NULL, NULL,
       'sr_analyst_williams', '2026-09-16 09:00:00 +0000'::TIMESTAMP_TZ, 'COMPLIANCE_TEAM',
       '2026-09-16 08:00:00 +0000'::TIMESTAMP_TZ
UNION ALL
-- RESOLVED_APPROVED: False positive (Luxury Motors)
SELECT 'CASE-2026-0007', 'ACC-000000000002',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Luxury Motors' LIMIT 1),
       '2026-09-22 13:00:00 +0000'::TIMESTAMP_TZ, 'HIGH_VALUE', 65, 'MEDIUM',
       PARSE_JSON('["amount_threshold"]')::ARRAY,
       'analyst_chen', 'RESOLVED_APPROVED',
       'False positive: $9,100 to Luxury Motors confirmed as legitimate vehicle purchase. Customer provided invoice.',
       '2026-09-22 13:00:00 +0000'::TIMESTAMP_TZ, 'analyst_chen', '2026-09-23 10:00:00 +0000'::TIMESTAMP_TZ,
       NULL, NULL, NULL,
       '2026-09-23 13:00:00 +0000'::TIMESTAMP_TZ
UNION ALL
-- CLOSED: Full investigation complete
SELECT 'CASE-2026-0008', 'ACC-000000000006',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Moscow Trade Center' LIMIT 1),
       '2026-09-10 09:00:00 +0000'::TIMESTAMP_TZ, 'WATCHLIST_MATCH', 75, 'HIGH',
       PARSE_JSON('["watchlist_match","high_risk_jurisdiction"]')::ARRAY,
       'sr_analyst_williams', 'CLOSED',
       'Investigation complete. Account frozen. SAR filed. Law enforcement notified via LE referral #2026-LE-0018.',
       '2026-09-10 09:00:00 +0000'::TIMESTAMP_TZ, 'sr_analyst_williams', '2026-09-15 17:00:00 +0000'::TIMESTAMP_TZ,
       'analyst_chen', '2026-09-12 11:00:00 +0000'::TIMESTAMP_TZ, 'COMPLIANCE_TEAM',
       '2026-09-11 09:00:00 +0000'::TIMESTAMP_TZ
);

-- ============================================================================
-- 5. CUSTOMER_VERIFICATION_EVENTS — 6 events covering all response types
-- ============================================================================
DELETE FROM AGENTS.CUSTOMER_VERIFICATION_EVENTS WHERE EVENT_ID LIKE 'VER-EVT-%';

INSERT INTO AGENTS.CUSTOMER_VERIFICATION_EVENTS (
  EVENT_ID, CASE_ID, ACCOUNT_ID, TXN_ID, VERIFICATION_METHOD, RESPONSE_TYPE,
  RESPONSE_TIMESTAMP, RESPONSE_TIME_MINUTES, DEVICE_FINGERPRINT, IP_ADDRESS,
  NOTES, ALERT_DISPATCHED_AT, EMAIL_STATUS, PUSH_STATUS, TOKEN_VALID,
  EXPLANATION_CUSTOMER, VERIFICATION_TOKEN, TOKEN_EXPIRES_AT
)
SELECT * FROM (
-- CONFIRMED_FRAUD: Customer says "wasn't me"
SELECT 'VER-EVT-001'::VARCHAR, 'CASE-2026-0003'::VARCHAR, 'ACC-000000000005'::VARCHAR,
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Darknet Market Supplies' LIMIT 1),
       'EMAIL'::VARCHAR, 'CONFIRMED_FRAUD'::VARCHAR,
       '2026-09-24 12:15:00 +0000'::TIMESTAMP_TZ, 75.0::NUMBER(5,1),
       'fp_abc123def456'::VARCHAR, '192.168.1.42'::VARCHAR,
       'Customer confirmed: did not authorize $9,800 transfer to Darknet Market Supplies'::VARCHAR,
       '2026-09-24 11:00:00 +0000'::TIMESTAMP_TZ, 'DELIVERED'::VARCHAR, NULL::VARCHAR, TRUE::BOOLEAN,
       NULL::VARCHAR, 'tok_a1b2c3d4e5f6'::VARCHAR, '2026-09-24 23:00:00'::TIMESTAMP_NTZ
UNION ALL
-- CONFIRMED_LEGITIMATE: Customer confirms transaction
SELECT 'VER-EVT-002', 'CASE-2026-0007', 'ACC-000000000002',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Luxury Motors' LIMIT 1),
       'EMAIL', 'CONFIRMED_LEGITIMATE',
       '2026-09-22 14:30:00 +0000'::TIMESTAMP_TZ, 90.0,
       'fp_xyz789ghi012', '10.0.0.55',
       'Customer confirmed: legitimate purchase of vehicle from Luxury Motors dealership',
       '2026-09-22 13:00:00 +0000'::TIMESTAMP_TZ, 'DELIVERED', NULL, TRUE,
       'I bought a car from Luxury Motors. Here is my invoice number: INV-2026-44821',
       'tok_g7h8i9j0k1l2', '2026-09-23 01:00:00'::TIMESTAMP_NTZ
UNION ALL
-- AWAITING_RESPONSE: Dispatched, no reply yet
SELECT 'VER-EVT-003', 'CASE-2026-0001', 'ACC-000000000003',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Golden Shell Exports' LIMIT 1),
       'EMAIL', 'AWAITING_RESPONSE',
       NULL::TIMESTAMP_TZ, NULL::NUMBER(5,1),
       NULL, NULL,
       'Verification alert dispatched to account holder. Awaiting response.',
       '2026-09-25 15:00:00 +0000'::TIMESTAMP_TZ, 'DELIVERED', NULL, TRUE,
       NULL, 'tok_m3n4o5p6q7r8', '2026-09-26 03:00:00'::TIMESTAMP_NTZ
UNION ALL
-- EXPIRED: Customer never responded
SELECT 'VER-EVT-004', 'CASE-2026-0005', 'ACC-000000000007',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='NovaCash Express Payments' LIMIT 1),
       'EMAIL', 'EXPIRED',
       NULL::TIMESTAMP_TZ, NULL::NUMBER(5,1),
       NULL, NULL,
       'Verification token expired after 12h with no customer response. Treated as non-cooperative.',
       '2026-09-20 11:00:00 +0000'::TIMESTAMP_TZ, 'DELIVERED', NULL, FALSE,
       NULL, 'tok_s9t0u1v2w3x4', '2026-09-20 23:00:00'::TIMESTAMP_NTZ
UNION ALL
-- DELIVERY_FAILED: Email bounced
SELECT 'VER-EVT-005', 'CASE-2026-0004', 'ACC-000000000009',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Petrokov Global Services' LIMIT 1),
       'EMAIL', 'DELIVERY_FAILED',
       NULL::TIMESTAMP_TZ, NULL::NUMBER(5,1),
       NULL, NULL,
       'Email delivery failed: mailbox not found. Account holder contact info may be fraudulent.',
       '2026-09-23 17:00:00 +0000'::TIMESTAMP_TZ, 'BOUNCED', NULL, FALSE,
       NULL, 'tok_y5z6a7b8c9d0', '2026-09-24 05:00:00'::TIMESTAMP_NTZ
UNION ALL
-- CONFIRMED_FRAUD via push: Second verification attempt
SELECT 'VER-EVT-006', 'CASE-2026-0008', 'ACC-000000000006',
       (SELECT TXN_ID FROM RAW.RAW_TRANSACTIONS WHERE MERCHANT='Moscow Trade Center' LIMIT 1),
       'PUSH', 'CONFIRMED_FRAUD',
       '2026-09-10 10:45:00 +0000'::TIMESTAMP_TZ, 105.0,
       'fp_qrs345tuv678', '203.0.113.99',
       'Customer confirmed fraud via push notification. Account frozen immediately.',
       '2026-09-10 09:00:00 +0000'::TIMESTAMP_TZ, NULL, 'DELIVERED', TRUE,
       'I did not make this payment to Moscow Trade Center. Please freeze my account.',
       'tok_e1f2g3h4i5j6', '2026-09-10 21:00:00'::TIMESTAMP_NTZ
);

-- ============================================================================
-- 6. SAR_FILINGS — 2 filings (FILED + PENDING)
-- ============================================================================
DELETE FROM AGENTS.SAR_FILINGS WHERE CASE_ID LIKE 'CASE-2026-%';

INSERT INTO AGENTS.SAR_FILINGS (FILING_ID, CASE_ID, OPENED_BY, OPENED_AT, FILING_DEADLINE, FILED_BY, FILED_AT, STATUS) VALUES
('SAR-2026-09-0042', 'CASE-2026-0006', 'sr_analyst_williams', '2026-09-16 09:00:00 +0000', '2026-09-30 23:59:00 +0000', 'compliance_officer_davis', '2026-09-18 11:00:00 +0000', 'FILED'),
('SAR-2026-09-0051', 'CASE-2026-0005', 'compliance_officer_davis', '2026-09-22 16:30:00 +0000', '2026-10-06 23:59:00 +0000', NULL, NULL, 'PENDING');

-- ============================================================================
-- 7. AGENT_AUDIT_LOG — 10 entries covering full case lifecycle
-- ============================================================================
DELETE FROM AGENTS.AGENT_AUDIT_LOG WHERE CASE_ID LIKE 'CASE-2026-%';

INSERT INTO AGENTS.AGENT_AUDIT_LOG (EVENT_ID, CASE_ID, ACTION_TAKEN, RESOLVED_BY, RESOLVED_AT, REVIEWER_NOTES) VALUES
(UUID_STRING(), 'CASE-2026-0001', 'FRAUD_DETECTION',         'SENTINEL_AI_ENGINE',      '2026-09-25 14:30:00 +0000', 'Agent detected watchlist match for Golden Shell Exports. Risk score: 92. Auto-generated alert.'),
(UUID_STRING(), 'CASE-2026-0003', 'CASE_ASSIGNED',           'system',                  '2026-09-24 11:05:00 +0000', 'Auto-assigned to analyst_chen based on workload balancing. SLA: 24h.'),
(UUID_STRING(), 'CASE-2026-0003', 'VERIFICATION_DISPATCHED', 'analyst_chen',             '2026-09-24 11:10:00 +0000', 'Email verification sent to account holder for ACC-000000000005.'),
(UUID_STRING(), 'CASE-2026-0003', 'VERIFICATION_RECEIVED',   'system',                  '2026-09-24 12:15:00 +0000', 'Customer confirmed fraud. Response time: 75 min. Proceeding with escalation.'),
(UUID_STRING(), 'CASE-2026-0004', 'CASE_ESCALATED',          'analyst_chen',             '2026-09-24 10:00:00 +0000', 'Escalated to COMPLIANCE_TEAM: multi-signal alert on ACC-000000000009 with Petrokov link.'),
(UUID_STRING(), 'CASE-2026-0006', 'REGULATORY_QUERY',        'compliance_officer_davis', '2026-09-16 10:00:00 +0000', 'Queried regulatory docs for OFAC sanctions requirements. Found: 31 CFR Part 501.'),
(UUID_STRING(), 'CASE-2026-0006', 'SAR_GENERATED',           'SENTINEL_AI_ENGINE',      '2026-09-17 09:00:00 +0000', 'AI-generated SAR narrative for CASE-2026-0006. 8 sections per FinCEN requirements.'),
(UUID_STRING(), 'CASE-2026-0006', 'SAR_FILED',               'compliance_officer_davis', '2026-09-18 11:00:00 +0000', 'SAR filed with FinCEN. Reference: SAR-2026-09-0042. Account frozen.'),
(UUID_STRING(), 'CASE-2026-0007', 'CASE_RESOLVED',           'analyst_chen',             '2026-09-23 10:00:00 +0000', 'Resolved as false positive. Customer confirmed legitimate vehicle purchase.'),
(UUID_STRING(), 'CASE-2026-0008', 'CASE_CLOSED',             'sr_analyst_williams',      '2026-09-15 17:00:00 +0000', 'Investigation complete. SAR filed. Account frozen. LE referral submitted.');

-- ============================================================================
-- 8. USER_ROLE_MAPPING — Analyst team members
-- ============================================================================
DELETE FROM AGENTS.USER_ROLE_MAPPING WHERE USER_NAME IN ('analyst_chen','sr_analyst_williams','compliance_officer_davis');

INSERT INTO AGENTS.USER_ROLE_MAPPING (MAPPING_ID, USER_NAME, ASSIGNED_ROLE, ASSIGNED_BY, ASSIGNED_AT, EXPIRES_AT, STATUS, APPROVED_BY) VALUES
(UUID_STRING(), 'analyst_chen',             'FRAUD_ANALYST',       'admin', '2026-01-15 09:00:00 +0000', NULL, 'ACTIVE', 'compliance_officer_davis'),
(UUID_STRING(), 'sr_analyst_williams',      'SENIOR_ANALYST',      'admin', '2025-06-01 09:00:00 +0000', NULL, 'ACTIVE', 'compliance_officer_davis'),
(UUID_STRING(), 'compliance_officer_davis', 'COMPLIANCE_OFFICER',  'admin', '2025-01-10 09:00:00 +0000', NULL, 'ACTIVE', 'admin');

-- ============================================================================
-- 9. DOCUMENT_CHUNKS — Regulatory text for Cortex Search RAG
-- ============================================================================
DELETE FROM DOCUMENTS.DOCUMENT_CHUNKS WHERE CHUNK_ID LIKE 'REG-%';

INSERT INTO DOCUMENTS.DOCUMENT_CHUNKS (CHUNK_ID, SOURCE_DOCUMENT, CHUNK_TEXT, PAGE_NUMBER) VALUES
('REG-BSA-001', 'Bank Secrecy Act (BSA) - 31 USC 5311-5332',
 'The Bank Secrecy Act requires financial institutions to assist U.S. government agencies in detecting and preventing money laundering. Institutions must file Currency Transaction Reports (CTRs) for cash transactions exceeding $10,000 and Suspicious Activity Reports (SARs) when they detect suspicious transactions that might signify money laundering, tax evasion, or other criminal activities. SAR filing is mandatory within 30 days of initial detection, with a 60-day extension if no suspect is identified.', 1),

('REG-BSA-002', 'Bank Secrecy Act (BSA) - 31 USC 5311-5332',
 'Structuring, also known as smurfing, is the practice of executing financial transactions in a specific pattern calculated to avoid triggering reporting requirements. Under 31 USC 5324, it is illegal to structure transactions to evade CTR filing requirements. Transactions that are broken into amounts just below $10,000 to avoid reporting are considered structuring. Penalties include up to 5 years imprisonment and fines up to $250,000.', 2),

('REG-OFAC-001', 'OFAC Sanctions Compliance - 31 CFR Part 501',
 'The Office of Foreign Assets Control (OFAC) administers and enforces economic sanctions programs against targeted foreign countries, terrorists, international narcotics traffickers, and those engaged in activities related to the proliferation of weapons of mass destruction. All U.S. persons must comply with OFAC regulations. The Specially Designated Nationals (SDN) List identifies individuals and entities whose assets are blocked. Financial institutions must screen all transactions against the SDN list and report any matches within 10 business days.', 1),

('REG-OFAC-002', 'OFAC Sanctions Compliance - 31 CFR Part 501',
 'Iran sanctions under Executive Order 13846 and the Iranian Transactions and Sanctions Regulations (ITSR) prohibit virtually all transactions involving Iran or Iranian nationals. This includes direct and indirect financial transactions, trade in goods and services, and investment activities. Violations can result in civil penalties up to $307,922 per violation or criminal penalties up to $1,000,000 and 20 years imprisonment. Financial institutions must implement robust screening programs to detect Iran-linked transactions.', 2),

('REG-AML-001', 'AML/KYC Requirements - FinCEN CDD Rule',
 'The Customer Due Diligence (CDD) Rule requires covered financial institutions to identify and verify the identity of beneficial owners of legal entity customers at account opening. The four core requirements are: (1) Customer Identification Program (CIP), (2) Customer Due Diligence, (3) Enhanced Due Diligence for high-risk customers, and (4) Ongoing monitoring for reporting suspicious transactions. Institutions must establish risk-based procedures for conducting ongoing CDD when a new account is opened and update customer information on a risk basis.', 1),

('REG-AML-002', 'AML/KYC Requirements - FinCEN CDD Rule',
 'Enhanced Due Diligence (EDD) is required for customers presenting higher risk including: politically exposed persons (PEPs), customers from high-risk jurisdictions identified by FATF, correspondent banking relationships, private banking accounts, and customers with complex ownership structures. EDD measures include obtaining additional identifying information, conducting more frequent reviews, monitoring transactions more closely, and obtaining senior management approval for establishing business relationships.', 2),

('REG-FATF-001', 'FATF Recommendations - High-Risk Jurisdictions',
 'The Financial Action Task Force (FATF) identifies jurisdictions with strategic AML/CFT deficiencies. High-risk jurisdictions subject to a Call for Action (blacklist) include: North Korea (DPRK), Iran, and Myanmar. Jurisdictions under increased monitoring (grey list) are subject to enhanced scrutiny. Financial institutions should apply enhanced due diligence measures proportionate to the risks arising from transactions involving these jurisdictions. Cross-border wire transfers involving high-risk jurisdictions require additional scrutiny and documentation.', 1),

('REG-SAR-001', 'SAR Filing Guidelines - FinCEN Advisory FIN-2026-A001',
 'Suspicious Activity Reports must contain: (1) Subject information including name, address, SSN/TIN, date of birth; (2) Suspicious activity details including dates, amounts, account numbers; (3) Narrative describing why the activity is suspicious including all relevant facts; (4) Supporting documentation references. The narrative is the most critical element and should describe the five Ws: who, what, when, where, and why. AI-assisted SAR generation is permissible provided a qualified compliance officer reviews and approves the filing before submission. Auto-generated narratives must be clearly marked as AI-assisted.', 1);

-- ============================================================================
-- DONE. Summary of seeded data:
--   RAW_WATCHLIST:                  6 entities
--   RAW_ACCOUNTS:                  12 accounts
--   RAW_TRANSACTIONS:              51 transactions
--   FRAUD_ALERTS:                   8 cases (all states)
--   CUSTOMER_VERIFICATION_EVENTS:   6 events (all response types)
--   SAR_FILINGS:                    2 filings (FILED + PENDING)
--   AGENT_AUDIT_LOG:               10 entries (full lifecycle)
--   USER_ROLE_MAPPING:              3 team members
--   DOCUMENT_CHUNKS:                8 regulatory chunks (RAG)
--
-- The Dynamic Table (CURATED.TRANSACTION_ENRICHED) will auto-refresh
-- within 5 minutes. The Cortex Search Service (REGULATORY_SEARCH_SVC)
-- will index document chunks within its 1-hour target lag.
-- ============================================================================
