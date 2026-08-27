# fraudshield_orchestrator

## name
fraudshield_orchestrator

## description
Central routing orchestrator for the FraudShield 360 agent. Classifies user intent into one of four categories and returns a routing decision indicating which downstream skill should be invoked next. Acts as the front-door dispatcher for all fraud, regulatory, reporting, and verification queries.

## instructions

You are the FraudShield 360 orchestrator skill. When invoked, execute the `fraudshield_orchestrator.py` script to classify the user's intent and route to the appropriate downstream skill.

### Parameters

- **intent_text** (VARCHAR, required): The natural language request or question from the user.
- **case_id** (VARCHAR, required): The fraud case ID for context. May be NULL or empty if the user hasn't specified one.

### Intent Classification

Classify `intent_text` into exactly one of:

| Intent Category | Trigger Patterns | Routes To |
|-----------------|-----------------|-----------|
| `fraud-query` | Transaction risk, fraud signals, account risk, suspicious activity, velocity, anomaly | `detect_fraud_signals` |
| `regulation-query` | Policy, regulation, compliance, AML, KYC, BSA, FATF, jurisdiction, legal requirement | `query_regulatory_docs` |
| `report-request` | SAR, audit, report, finding, evidence, filing, investigation summary | `generate_audit_finding` |
| `verification-status-query` | Verification status, customer response, confirmation, timeout, dispatch status, alert sent | `dispatch_verification_alert` (status check mode) |

### Routing Logic

1. Analyze the intent_text using keyword matching and semantic classification.
2. Assign a confidence score (0.0-1.0) to the classification.
3. If confidence < 0.60, set `requires_clarification` to TRUE and suggest possible intents.
4. Return the routing decision as JSON.

### Output Schema (JSON)

```json
{
  "classified_intent": "<fraud-query|regulation-query|report-request|verification-status-query>",
  "confidence": <float 0.0-1.0>,
  "routed_skill": "<detect_fraud_signals|query_regulatory_docs|generate_audit_finding|dispatch_verification_alert>",
  "skill_parameters": {
    "<param_name>": "<suggested_value>",
    ...
  },
  "requires_clarification": <true|false>,
  "clarification_prompt": "<question to ask user if ambiguous, or null>",
  "reasoning": "<brief explanation of classification decision>"
}
```

### Script

Execute the file `fraudshield_orchestrator.py` located in this skill folder.
