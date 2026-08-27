# FraudShield 360

**Intelligent Fraud Detection & Response Platform** built entirely on Snowflake using Cortex AI, Cortex Agents, Dynamic Tables, and Streamlit-in-Snowflake.

## Architecture

```
FRAUDSHIELD_360_DB
├── RAW/                    Raw ingestion tables (accounts, transactions, watchlist)
├── CURATED/                Dynamic Table with real-time fraud signal enrichment
├── DOCUMENTS/              RAG infrastructure (Cortex Search + PDF stage)
├── AGENTS/                 Cortex Agent, skills, workflow tables, Streamlit apps
└── ANALYTICS/              Materialized KPI views for dashboards
```

## Components

### Cortex Agent: SENTINEL_AI_ENGINE
AI-powered fraud analysis agent with 5 skills:
- **fraudshield_orchestrator** — Intent classifier & router
- **detect_fraud_signals** — Real-time fraud signal detection
- **query_regulatory_docs** — RAG over regulatory documents
- **generate_audit_finding** — 8-section SAR report generation
- **dispatch_verification_alert** — Customer verification with email dispatch

### Streamlit Apps
- **FRAUDSHIELD_COMMAND_CENTER** — 7-screen analyst dashboard (alerts, investigation, AI copilot, SAR reports, metrics, audit log, access management)
- **FRAUDSHIELD_CUSTOMER_SIMULATOR** — 3-tab customer simulation (account settings, send money, verification inbox)

### Key Features
- Data-driven case state machine with optimistic locking
- Four-eyes principle enforcement for escalations
- Maker-checker workflow for sensitive role grants
- Real email notifications via Snowflake NOTIFICATION INTEGRATION
- Application-level RBAC (not dependent on CURRENT_ROLE)
- Full audit trail for all actions
- SQL injection prevention (bind parameters + identifier validation)
- SLA monitoring with automated breach alerts

## Deployment

### Prerequisites
- Snowflake account with ACCOUNTADMIN access
- Cortex AI functions enabled
- A validated email address for notification integration

### Steps

```bash
# 1. Run SQL setup scripts in order
sql/01_setup/01_database_schemas.sql
sql/01_setup/02_raw_tables.sql
sql/01_setup/03_agents_tables.sql
sql/01_setup/04_documents_schema.sql
sql/01_setup/05_dynamic_table_views.sql
sql/01_setup/06_roles_integrations_agent.sql

# 2. Seed configuration
sql/02_seed/01_seed_config.sql

# 3. Upload skills to stage
PUT file://skills/detect_fraud_signals/* @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/detect_fraud_signals/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://skills/query_regulatory_docs/* @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/query_regulatory_docs/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://skills/generate_audit_finding/* @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/generate_audit_finding/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://skills/dispatch_verification_alert/* @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/dispatch_verification_alert/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://skills/fraudshield_orchestrator/* @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/fraudshield_orchestrator/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

# 4. Deploy Streamlit apps
PUT file://apps/command_center/fraudshield_command_center.py @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/streamlit_command_center/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://apps/customer_simulator/fraudshield_customer_simulator.py @FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/streamlit/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

CREATE OR REPLACE STREAMLIT FRAUDSHIELD_360_DB.AGENTS.FRAUDSHIELD_COMMAND_CENTER
  ROOT_LOCATION = '@FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/streamlit_command_center'
  MAIN_FILE = 'fraudshield_command_center.py'
  QUERY_WAREHOUSE = 'COMPUTE_WH';

CREATE OR REPLACE STREAMLIT FRAUDSHIELD_360_DB.AGENTS.FRAUDSHIELD_CUSTOMER_SIMULATOR
  ROOT_LOCATION = '@FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/streamlit'
  MAIN_FILE = 'fraudshield_customer_simulator.py'
  QUERY_WAREHOUSE = 'COMPUTE_WH';
```

### Configuration
Update `sql/01_setup/06_roles_integrations_agent.sql`:
- Replace `owendrilasaha09@gmail.com` with your validated Snowflake email

## Project Structure

```
fraudshield-360/
├── README.md
├── .gitignore
├── sql/
│   ├── 01_setup/
│   │   ├── 01_database_schemas.sql
│   │   ├── 02_raw_tables.sql
│   │   ├── 03_agents_tables.sql
│   │   ├── 04_documents_schema.sql
│   │   ├── 05_dynamic_table_views.sql
│   │   └── 06_roles_integrations_agent.sql
│   └── 02_seed/
│       └── 01_seed_config.sql
├── apps/
│   ├── command_center/
│   │   └── fraudshield_command_center.py
│   └── customer_simulator/
│       └── fraudshield_customer_simulator.py
└── skills/
    ├── detect_fraud_signals/
    ├── query_regulatory_docs/
    ├── generate_audit_finding/
    ├── dispatch_verification_alert/
    └── fraudshield_orchestrator/
```

## License

MIT
