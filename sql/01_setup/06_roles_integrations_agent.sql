-- ============================================================================
-- FraudShield 360 - Roles, Integrations & Agent
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- Roles
CREATE ROLE IF NOT EXISTS FRAUD_ANALYST_ROLE;
CREATE ROLE IF NOT EXISTS COMPLIANCE_OFFICER_ROLE;
CREATE ROLE IF NOT EXISTS AUDIT_ROLE;
CREATE ROLE IF NOT EXISTS FRAUDSHIELD_ACCESS_ADMIN_ROLE;
CREATE ROLE IF NOT EXISTS COCO_AUTOMATION_ROLE;

-- Email Notification Integration
CREATE OR REPLACE NOTIFICATION INTEGRATION FRAUDSHIELD_EMAIL_INT
  TYPE = EMAIL
  ENABLED = TRUE
  ALLOWED_RECIPIENTS = ('owendrilasaha09@gmail.com');  -- Update with your validated email

GRANT USAGE ON INTEGRATION FRAUDSHIELD_EMAIL_INT TO ROLE SYSADMIN;
GRANT USAGE ON INTEGRATION FRAUDSHIELD_EMAIL_INT TO ROLE COCO_AUTOMATION_ROLE;

-- Grants
GRANT USAGE ON DATABASE FRAUDSHIELD_360_DB TO ROLE FRAUD_ANALYST_ROLE;
GRANT USAGE ON DATABASE FRAUDSHIELD_360_DB TO ROLE COMPLIANCE_OFFICER_ROLE;
GRANT USAGE ON DATABASE FRAUDSHIELD_360_DB TO ROLE AUDIT_ROLE;

GRANT USAGE ON SCHEMA FRAUDSHIELD_360_DB.AGENTS TO ROLE FRAUD_ANALYST_ROLE;
GRANT USAGE ON SCHEMA FRAUDSHIELD_360_DB.AGENTS TO ROLE COMPLIANCE_OFFICER_ROLE;
GRANT USAGE ON SCHEMA FRAUDSHIELD_360_DB.AGENTS TO ROLE AUDIT_ROLE;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA FRAUDSHIELD_360_DB.AGENTS TO ROLE COMPLIANCE_OFFICER_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA FRAUDSHIELD_360_DB.AGENTS TO ROLE FRAUD_ANALYST_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA FRAUDSHIELD_360_DB.AGENTS TO ROLE AUDIT_ROLE;

-- Skill Stage
CREATE STAGE IF NOT EXISTS FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE
  DIRECTORY = (ENABLE = TRUE);

-- Cortex Agent
CREATE OR REPLACE AGENT FRAUDSHIELD_360_DB.AGENTS.SENTINEL_AI_ENGINE
  COMMENT = 'FraudShield 360 AI engine - orchestrates fraud detection, regulatory compliance, audit reporting, and customer verification workflows'
  PROFILE = '{"display_name": "Sentinel AI Engine", "color": "red"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto

  orchestration:
    budget:
      seconds: 60
      tokens: 50000

  instructions:
    response: "You are Sentinel AI, the FraudShield 360 fraud detection and compliance engine. Provide precise, evidence-based responses. Always cite signal IDs, risk scores, and source documents. Never speculate beyond what the data shows."
    orchestration: "Route requests through the fraudshield_orchestrator skill first to classify intent. For fraud queries use detect_fraud_signals. For regulatory questions use query_regulatory_docs. For audit reports use generate_audit_finding. For dispatching customer alerts use dispatch_verification_alert."
    sample_questions:
      - question: "What are the fraud signals for account ACC-000000000042 in the last 24 hours?"
      - question: "What does EU AML regulation say about transaction monitoring thresholds?"
      - question: "Generate a SAR report for case abc-123-def"
      - question: "Send a verification alert to the customer for transaction TXN-001"

  skills:
    - name: "fraudshield_orchestrator"
      source:
        type: "STAGE"
        path: "@FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/fraudshield_orchestrator"
    - name: "detect_fraud_signals"
      source:
        type: "STAGE"
        path: "@FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/detect_fraud_signals"
    - name: "query_regulatory_docs"
      source:
        type: "STAGE"
        path: "@FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/query_regulatory_docs"
    - name: "generate_audit_finding"
      source:
        type: "STAGE"
        path: "@FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/generate_audit_finding"
    - name: "dispatch_verification_alert"
      source:
        type: "STAGE"
        path: "@FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE/skills/dispatch_verification_alert"
  $$;
