# FraudShield 360

**Intelligent Fraud Detection & Response Platform** built entirely on Snowflake.

Combines Cortex AI, Cortex Agents, Dynamic Tables, Cortex Search, and Streamlit-in-Snowflake into an end-to-end fraud operations system with enterprise-grade security, audit trails, and real-time alerting.

---

## Architecture

```
FRAUDSHIELD_360_DB
├── RAW/                     Ingestion tables (accounts, transactions, watchlist)
├── CURATED/                 Dynamic Table — real-time fraud signal enrichment (6 signals, risk scoring)
├── DOCUMENTS/               RAG infrastructure (Cortex Search + regulatory document chunks)
├── AGENTS/                  Cortex Agent, 5 AI skills, workflow tables, Streamlit apps
└── ANALYTICS/               5 KPI views for dashboards
```

### Data Flow

```
RAW_TRANSACTIONS + RAW_ACCOUNTS + RAW_WATCHLIST
        │
        ▼
┌─────────────────────────────────────────┐
│  DYNAMIC TABLE: TRANSACTION_ENRICHED    │
│  (5-min lag, 6 fraud signals, scoring)  │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
  FRAUD_ALERTS    ANALYTICS VIEWS
  (state machine)  (5 dashboards)
        │
        ▼
┌─────────────────────────────────────────┐
│  CORTEX AGENT: SENTINEL_AI_ENGINE       │
│  5 skills → detect, classify, report,   │
│  verify, query regulations              │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
  SAR_FILINGS    VERIFICATION_EVENTS
  (FinCEN)       (customer alerts + email)
```

---

## Components

### Cortex Agent: SENTINEL_AI_ENGINE

| Skill | Purpose |
|-------|---------|
| `fraudshield_orchestrator` | Intent classifier — routes queries to the right skill |
| `detect_fraud_signals` | Real-time fraud signal detection for an account |
| `query_regulatory_docs` | RAG over regulatory documents with confidence guardrail |
| `generate_audit_finding` | 8-section SAR report generation with regulatory citations |
| `dispatch_verification_alert` | Dual-mode: dispatch verification + status check |

### Dynamic Table: TRANSACTION_ENRICHED

Six fraud signals computed in real-time with weighted scoring:

| Signal | Weight | Logic |
|--------|--------|-------|
| Watchlist Match | 30 | Merchant name fuzzy-matches sanctions list |
| Amount Anomaly | 25 | Amount > 5x account median |
| Geo Mismatch | 20 | Transaction country != account domicile |
| Structuring | 20 | Amount in $9,000-$9,999 range (just-below-threshold) |
| Velocity | 15 | 4+ transactions within 1 hour |
| Round Number | 5 | Amount is exact multiple of $1,000 |

Risk tiers: **CRITICAL** (75+), **HIGH** (50-74), **MEDIUM** (25-49), **LOW** (0-24)

### Streamlit Apps

**FRAUDSHIELD_COMMAND_CENTER** (7 screens):
1. **Command Center** — Live alert feed with risk badges and severity filters
2. **Case Investigator** — Deep-dive with data-driven state machine, optimistic locking
3. **CoCo Chat** — AI copilot powered by Cortex Agent (DATA_AGENT_RUN)
4. **Report Preview** — SAR generation with DRAFT watermark + PDF export
5. **Metrics Dashboard** — KPI cards, charts, SLA breach monitoring
6. **Audit Log** — Read-only audit trail (AUDIT_ROLE + COMPLIANCE_OFFICER only)
7. **Access Management** — User lifecycle, maker-checker, offboarding (admin only)

**FRAUDSHIELD_CUSTOMER_SIMULATOR** (3 tabs):
1. **Account Settings** — Configure simulated customer profile
2. **Send Money** — Submit transactions, auto-triggers fraud detection + email alerts
3. **Verification Inbox** — Accept/Hold/Reject pending verification alerts

### Security Features

- Application-level RBAC via USER_ROLE_MAPPING (not CURRENT_ROLE)
- Data-driven case state machine with optimistic locking (ROW_VERSION)
- Four-eyes principle on escalation approvals
- Analyst self-approval threshold (configurable risk score + tier)
- Maker-checker workflow for COMPLIANCE_OFFICER_ROLE grants
- SQL injection prevention (bind parameters + identifier validation)
- No PII in AI prompts
- Generic error messages (details logged server-side only)
- Full audit trail for every action (case views, transitions, user management)
- Real email notifications for escalations and SLA breaches

---

## Deployment

### Prerequisites

- Snowflake account with ACCOUNTADMIN
- Cortex AI functions enabled in your region
- At least one validated email address for notifications

### Step 1: Run SQL Setup

Open `sql/01_complete_setup.sql` in a Snowflake worksheet and execute. This creates:
- Database, 5 schemas, warehouse
- All 15+ tables with correct schemas
- Dynamic table, Cortex Search service, 5 analytics views
- Roles, grants, notification integration
- State machine transitions + app config seed data

### Step 2: Upload Files to Stage

Run `deploy.ps1` from the project root:

```powershell
.\deploy.ps1
```

This uploads all 5 skills (SKILL.md + .py each) and both Streamlit apps to `@SKILL_STAGE`. If SnowSQL is not available, copy the printed PUT commands into a Snowflake worksheet.

### Step 3: Create Agent & Apps

Run `sql/02_deploy_agent_apps.sql` in a worksheet. This creates:
- SENTINEL_AI_ENGINE Cortex Agent with all 5 skills
- Both Streamlit apps (FRAUDSHIELD_COMMAND_CENTER, FRAUDSHIELD_CUSTOMER_SIMULATOR)

### Step 4: Load Demo Data

Run `sql/03_seed_demo_data.sql` in a worksheet. This populates:
- 6 watchlist entities (OFAC, INTERPOL, EU, FATF)
- 12 accounts across 8 countries with varied KYC/risk profiles
- 51 transactions designed to trigger all 6 fraud signals
- 8 fraud alert cases across all state machine states
- 6 customer verification events (all response types)
- 2 SAR filings (FILED + PENDING)
- 10 agent audit log entries (full case lifecycle)
- 3 analyst team members
- 8 regulatory document chunks for Cortex Search RAG

Wait ~5 minutes for the Dynamic Table to refresh and ~1 hour for Cortex Search to index.

### Step 5: Configuration

1. Update `ALLOWED_RECIPIENTS` in `01_complete_setup.sql` with your validated Snowflake email
2. The deploying user is auto-assigned FRAUDSHIELD_ACCESS_ADMIN_ROLE
3. Create additional users via the Access Management screen

---

## Demo Walkthrough

Six scenarios to demonstrate the full platform to judges:

### Scenario 1: Command Center Overview

Open **FRAUDSHIELD_COMMAND_CENTER** in Snowsight. The Command Center tab shows:
- 8 active cases across all states (OPEN through CLOSED)
- Color-coded risk badges (CRITICAL=red, HIGH=orange, MEDIUM=yellow)
- Filter by status, risk tier, or alert type
- Each case links to the Case Investigator

### Scenario 2: Case Investigation Workflow

Click into **CASE-2026-0003** (UNDER_REVIEW, Darknet Market Supplies):
- View triggered signals: watchlist match + geo mismatch + velocity
- See the data-driven state machine — only valid transitions are enabled
- Try transitioning to ESCALATED (requires COMPLIANCE_OFFICER role)
- Optimistic locking prevents concurrent updates via ROW_VERSION

### Scenario 3: AI Copilot (CoCo Chat)

Navigate to the **CoCo Chat** tab. Try these queries:
- "Is there any fraud in the last 7 days?" — triggers population-level scan
- "What are the fraud signals for ACC-000000000003?" — account-specific analysis
- "What does regulation say about structuring?" — RAG over regulatory documents
- "Generate a SAR report for CASE-2026-0006" — 8-section compliance report

### Scenario 4: SAR Report Generation

Go to **Report Preview** tab:
- Select CASE-2026-0006 (Iran sanctions violation, SAR_FILED)
- Click Generate — the Cortex Agent produces an 8-section SAR narrative
- DRAFT watermark is applied until compliance officer approval
- Export to PDF for filing

### Scenario 5: Customer Simulator (End-to-End Flow)

Open **FRAUDSHIELD_CUSTOMER_SIMULATOR** in a second browser tab:
1. **Account Settings** — Select ACC-000000000004 (Diana Chen)
2. **Send Money** — Send $9,500 to "Shell Company Services" in KY (Cayman Islands)
3. Watch: transaction is inserted, DT enriches it within 5 minutes, risk score is computed
4. If HIGH/CRITICAL: alert is auto-created, verification email is dispatched
5. **Verification Inbox** — Respond as the customer (Confirm Fraud / Confirm Legitimate)
6. Switch back to Command Center — new alert appears in the feed

### Scenario 6: Audit & Compliance

- **Audit Log** tab: View the full chronological audit trail for any case
- **Metrics Dashboard**: KPI cards show flag rates, avg risk scores, SLA breach counts
- **Access Management**: Demonstrate maker-checker for COMPLIANCE_OFFICER role grants

---

## Hackathon Scoring Alignment

### Technical Execution (40%)

| Criteria | Implementation |
|----------|---------------|
| Snowflake-native architecture | All components run inside Snowflake — no external services |
| Cortex Agent with 5 skills | SENTINEL_AI_ENGINE with orchestrator, detector, RAG, SAR, verification |
| Dynamic Table | TRANSACTION_ENRICHED with 6 fraud signals, 5-min lag, weighted scoring |
| Cortex Search (RAG) | REGULATORY_SEARCH_SVC over 8 regulatory document chunks |
| Real-time data pipeline | RAW → CURATED (DT) → AGENTS (alerts) → ANALYTICS (views) |
| SQL injection prevention | Bind parameters, regex validation, identifier allowlists |

### Real-World Relevance (30%)

| Criteria | Implementation |
|----------|---------------|
| AML/KYC compliance | BSA, OFAC, FATF, FinCEN regulatory framework |
| Full case lifecycle | OPEN → UNDER_REVIEW → ESCALATED → PENDING_SAR → SAR_FILED → CLOSED |
| Customer verification | Real email dispatch via SYSTEM$SEND_EMAIL with token-based verification |
| SAR report generation | AI-assisted 8-section narratives per FinCEN requirements |
| Regulatory RAG | Grounded responses with citation confidence scoring |
| Dual-persona design | Analyst Command Center + Customer Simulator |

### Solution Completeness (30%)

| Criteria | Implementation |
|----------|---------------|
| 7-screen analyst dashboard | Command Center, Investigator, CoCo Chat, Reports, Metrics, Audit, Access |
| 3-tab customer simulator | Settings, Send Money, Verification Inbox |
| RBAC with maker-checker | 5 roles, four-eyes principle, configurable thresholds |
| Full audit trail | Every action logged with actor, timestamp, details |
| Demo-ready data | 51 transactions, 8 cases, 6 verifications, regulatory docs |
| State machine | 11 valid transitions with role-based guards |

---

## Project Structure

```
fraudshield-360/
├── README.md
├── .gitignore
├── deploy.ps1                                  # Upload helper script
├── sql/
│   ├── 01_complete_setup.sql                   # All DDL, grants, seed data
│   ├── 02_deploy_agent_apps.sql                # Agent + Streamlit creation
│   └── 03_seed_demo_data.sql                   # Demo data (re-runnable)
├── apps/
│   ├── command_center/
│   │   └── fraudshield_command_center.py       # 7-screen analyst dashboard (2139 lines)
│   └── customer_simulator/
│       └── fraudshield_customer_simulator.py   # 3-tab customer sim (671 lines)
└── skills/
    ├── detect_fraud_signals/                   # SKILL.md + .py
    ├── query_regulatory_docs/                  # SKILL.md + .py
    ├── generate_audit_finding/                 # SKILL.md + .py
    ├── dispatch_verification_alert/            # SKILL.md + .py
    └── fraudshield_orchestrator/               # SKILL.md + .py
```

## Tech Stack

- **Snowflake Cortex AI** — LLM inference (COMPLETE, AI functions)
- **Cortex Agents** — Multi-skill AI orchestration with DATA_AGENT_RUN
- **Cortex Search** — RAG over regulatory documents
- **Dynamic Tables** — Real-time fraud signal enrichment (5-min lag)
- **Streamlit-in-Snowflake** — Enterprise web applications
- **Notification Integration** — Real email alerts via SYSTEM$SEND_EMAIL

## License

MIT
