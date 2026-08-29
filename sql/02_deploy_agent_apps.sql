-- ============================================================================
-- FraudShield 360 — Deploy Agent & Streamlit Apps
-- Run AFTER uploading skills and apps to stage via deploy.ps1
-- ============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE FRAUDSHIELD_360_DB;

-- Cortex Agent: SENTINEL_AI_ENGINE
CREATE OR REPLACE AGENT AGENTS.SENTINEL_AI_ENGINE
  COMMENT = 'FraudShield 360 AI engine'
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
    response: "You are Sentinel AI, the FraudShield 360 fraud detection and compliance engine. Provide precise, evidence-based responses. Always cite signal IDs, risk scores, and source documents."
    orchestration: "Route through fraudshield_orchestrator first. For fraud queries use detect_fraud_signals. For regulatory questions use query_regulatory_docs. For audit reports use generate_audit_finding. For customer alerts use dispatch_verification_alert."
    sample_questions:
      - question: "What are the fraud signals for account ACC-000000000042?"
      - question: "What does EU AML regulation say about transaction monitoring thresholds?"
      - question: "Generate a SAR report for case abc-123-def"
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

-- Streamlit Apps
CREATE OR REPLACE STREAMLIT AGENTS.FRAUDSHIELD_COMMAND_CENTER
  ROOT_LOCATION = '@AGENTS.SKILL_STAGE/streamlit_command_center'
  MAIN_FILE = 'fraudshield_command_center.py'
  QUERY_WAREHOUSE = 'COMPUTE_WH';

CREATE OR REPLACE STREAMLIT AGENTS.FRAUDSHIELD_CUSTOMER_SIMULATOR
  ROOT_LOCATION = '@AGENTS.SKILL_STAGE/streamlit'
  MAIN_FILE = 'fraudshield_customer_simulator.py'
  QUERY_WAREHOUSE = 'COMPUTE_WH';
