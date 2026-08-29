# FraudShield 360

**Intelligent Fraud Detection & Response Platform** built entirely on Snowflake.

Combines Cortex AI, Cortex Agents, Dynamic Tables, Cortex Search, and Streamlit-in-Snowflake into an end-to-end fraud operations system with enterprise-grade security, audit trails, and real-time alerting.

---

## Architecture

```
FRAUDSHIELD_360_DB
├── RAW/                     Ingestion tables (accounts, transactions, watchlist, verification responses)
├── CURATED/                 Dynamic Table — real-time fraud signal enrichment (6 signals, risk scoring)
├── DOCUMENTS/               RAG infrastructure (Cortex Search + internal PDF stage)
├── AGENTS/                  Cortex Agent, 5 AI skills, workflow tables, Streamlit apps
└── ANALYTICS/               5 materialized KPI views for dashboards
```

## Components

### Cortex Agent: SENTINEL_AI_ENGINE

| Skill | Purpose |
|-------|---------|
| `fraudshield_orchestrator` | Intent classifier — routes queries to the right skill |
| `detect_fraud_signals` | Real-time fraud signal detection for an account |
| `query_regulatory_docs` | RAG over regulatory PDFs with confidence guardrail |
| `generate_audit_finding` | 8-section SAR report generation |
| `dispatch_verification_alert` | Customer verification with JWT token + real email |

### Streamlit Apps

**FRAUDSHIELD_COMMAND_CENTER** (7 screens):
1. Command Center — Live alert feed with risk badges
2. Case Investigator — Deep-dive with data-driven state machine
3. CoCo Chat — AI copilot powered by Cortex COMPLETE
4. Report Preview — SAR generation with DRAFT watermark + PDF export
5. Metrics Dashboard — KPI cards, charts, SLA breach monitoring
6. Audit Log — Read-only audit trail (AUDIT_ROLE + COMPLIANCE_OFFICER only)
7. Access Management — User lifecycle, maker-checker, offboarding (admin only)

**FRAUDSHIELD_CUSTOMER_SIMULATOR** (3 tabs):
1. Account Settings — Configure simulated customer profile
2. Send Money — Submit transactions, auto-triggers fraud detection + email alerts
3. Verification Inbox — Accept/Hold/Reject pending verification alerts

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
- Database, schemas, warehouse
- All 15+ tables with correct schemas
- Dynamic table, Cortex Search service, 5 analytics views
- Roles, grants, notification integration
- State machine transitions + app config seed data

### Step 2: Upload Files to Stage
Run the PUT commands from `deploy.ps1`, or execute them manually in a worksheet:

```sql
-- Skills (run for each skill folder)
PUT file:///path/to/skills/detect_fraud_signals/SKILL.md @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/detect_fraud_signals/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/skills/detect_fraud_signals/detect_fraud_signals.py @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/detect_fraud_signals/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- ... repeat for all 5 skills

-- Streamlit apps
PUT file:///path/to/apps/command_center/fraudshield_command_center.py @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/streamlit_command_center/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file:///path/to/apps/customer_simulator/fraudshield_customer_simulator.py @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/streamlit/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
```

### Step 3: Create Agent & Apps
Run `sql/02_deploy_agent_apps.sql` in a worksheet. This creates:
- SENTINEL_AI_ENGINE Cortex Agent with all 5 skills
- Both Streamlit apps

### Step 4: Configuration
1. Update `ALLOWED_RECIPIENTS` in the notification integration with your validated email
2. The deploying user is auto-assigned FRAUDSHIELD_ACCESS_ADMIN_ROLE
3. Create additional users via the Access Management screen

---

## Project Structure

```
fraudshield-360/
├── README.md
├── .gitignore
├── deploy.ps1                              # Upload helper script
├── sql/
│   ├── 01_complete_setup.sql               # All DDL, grants, seed data
│   └── 02_deploy_agent_apps.sql            # Agent + Streamlit creation
├── apps/
│   ├── command_center/
│   │   └── fraudshield_command_center.py   # 7-screen analyst dashboard
│   └── customer_simulator/
│       └── fraudshield_customer_simulator.py  # 3-tab customer sim
└── skills/
    ├── detect_fraud_signals/               # SKILL.md + .py
    ├── query_regulatory_docs/              # SKILL.md + .py
    ├── generate_audit_finding/             # SKILL.md + .py
    ├── dispatch_verification_alert/        # SKILL.md + .py
    └── fraudshield_orchestrator/           # SKILL.md + .py
```

## Tech Stack
- **Snowflake Cortex AI** — LLM inference (COMPLETE, AI functions)
- **Cortex Agents** — Multi-skill AI orchestration
- **Cortex Search** — RAG over regulatory documents
- **Dynamic Tables** — Real-time fraud signal enrichment
- **Streamlit-in-Snowflake** — Enterprise web applications
- **Notification Integration** — Real email alerts via SYSTEM$SEND_EMAIL

## License
MIT
