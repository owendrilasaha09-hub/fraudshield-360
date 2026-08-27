# generate_audit_finding

## name
generate_audit_finding

## description
Generates a structured 8-section Suspicious Activity Report (SAR) for a given case ID. Joins FRAUD_ALERTS, TRANSACTION_ENRICHED, and CUSTOMER_VERIFICATION_EVENTS to produce a complete evidence-backed audit finding. Section 4 (Evidence Chain) explicitly includes the customer's verification response status.

## instructions

You are an audit report generation skill. When invoked, execute the `generate_audit_finding.py` script to produce a formal SAR report for a specific fraud case.

### Parameters

- **case_id** (VARCHAR, required): The fraud alert case identifier (UUID format) to generate the report for.

### Behavior

1. Query `FRAUDSHIELD_360_DB.AGENTS.FRAUD_ALERTS` for the case metadata.
2. Join `FRAUDSHIELD_360_DB.CURATED.TRANSACTION_ENRICHED` on TXN_ID to get full transaction details and signal data.
3. Join `FRAUDSHIELD_360_DB.AGENTS.CUSTOMER_VERIFICATION_EVENTS` on CASE_ID to get the customer's verification response.
4. Assemble an 8-section SAR report as structured TEXT.

### Output Format (TEXT)

The report must contain exactly 8 sections in this order:

```
=== SUSPICIOUS ACTIVITY REPORT ===
Case ID: <case_id>
Generated: <timestamp>

--- SECTION 1: EXECUTIVE SUMMARY ---
<Brief overview of the alert, risk tier, and recommendation>

--- SECTION 2: SUBJECT IDENTIFICATION ---
<Account ID, account type, domicile country, onboarding date, KYC status, risk tier>

--- SECTION 3: TRANSACTION DETAILS ---
<TXN_ID, timestamp, amount, merchant, channel, geo_country, geo_city, device_id>

--- SECTION 4: EVIDENCE CHAIN ---
<All triggered signals with descriptions>
<Customer verification response status: USER_CONFIRMED / USER_REQUESTED_REVIEW / USER_REJECTED / VERIFICATION_TIMEOUT>
<Verification method, response time, device fingerprint>

--- SECTION 5: RISK ASSESSMENT ---
<Composite risk score, risk tier, individual signal weights, explanation_admin>

--- SECTION 6: PATTERN ANALYSIS ---
<Historical context: number of alerts for this account, frequency of signals, behavioral baseline deviations>

--- SECTION 7: REGULATORY IMPLICATIONS ---
<Applicable reporting thresholds, BSA/AML considerations, recommended filing actions>

--- SECTION 8: RECOMMENDED ACTIONS ---
<Immediate actions, escalation path, monitoring recommendations, SAR filing recommendation>

=== END OF REPORT ===
```

### Critical Requirement

Section 4 (Evidence Chain) MUST explicitly include the customer's verification response status value (one of: USER_CONFIRMED, USER_REQUESTED_REVIEW, USER_REJECTED, VERIFICATION_TIMEOUT). This is a mandatory audit field.

### Script

Execute the file `generate_audit_finding.py` located in this skill folder.
