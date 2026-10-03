import json
import re
import _snowflake

# Parameters injected by skill runtime
intent_text = intent_text  # noqa: F841
case_id = case_id if 'case_id' in dir() and case_id else None  # noqa: F841

# --- Input validation ---
if not isinstance(intent_text, str) or len(intent_text.strip()) == 0:
    print(json.dumps({"error": "intent_text is required"}))
    raise SystemExit(0)
intent_text = intent_text[:1000]

if case_id is not None:
    if not isinstance(case_id, str) or not re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', case_id):
        case_id = None

# Intent classification via keyword/pattern scoring
intent_text_lower = intent_text.lower() if intent_text else ""

# Define keyword groups for each intent category
INTENT_PATTERNS = {
    "fraud-query": {
        "keywords": [
            "fraud", "suspicious", "risk", "signal", "velocity", "anomaly",
            "transaction risk", "account risk", "flagged", "alert score",
            "geo mismatch", "structuring", "watchlist", "amount anomaly",
            "fraud signals", "risk score", "risk tier", "detect"
        ],
        "skill": "detect_fraud_signals",
        "weight": 0
    },
    "regulation-query": {
        "keywords": [
            "regulation", "regulatory", "policy", "compliance", "aml",
            "kyc", "bsa", "fatf", "jurisdiction", "legal", "requirement",
            "rule", "guideline", "threshold", "reporting obligation",
            "sanctions", "ofac", "ctf", "cdd", "edd", "pep"
        ],
        "skill": "query_regulatory_docs",
        "weight": 0
    },
    "report-request": {
        "keywords": [
            "report", "sar", "audit", "finding", "evidence", "filing",
            "investigation", "summary", "generate report", "audit finding",
            "suspicious activity report", "document", "case report",
            "produce", "create report", "compile"
        ],
        "skill": "generate_audit_finding",
        "weight": 0
    },
    "verification-status-query": {
        "keywords": [
            "verification", "verified", "confirm", "confirmed", "customer response",
            "timeout", "user_confirmed", "user_rejected", "user_requested_review",
            "verification_timeout", "dispatch", "alert sent", "notification status",
            "push status", "email status", "pending response", "awaiting"
        ],
        "skill": "dispatch_verification_alert",
        "weight": 0
    }
}

# Score each intent category
for intent, config in INTENT_PATTERNS.items():
    score = 0
    for keyword in config["keywords"]:
        if keyword in intent_text_lower:
            # Longer keyword matches get higher weight
            score += len(keyword.split())
    config["weight"] = score

# Find the best match
best_intent = max(INTENT_PATTERNS.keys(), key=lambda k: INTENT_PATTERNS[k]["weight"])
best_score = INTENT_PATTERNS[best_intent]["weight"]
total_score = sum(c["weight"] for c in INTENT_PATTERNS.values())

# Calculate confidence
if total_score > 0:
    confidence = round(min(1.0, best_score / max(total_score, 1) + 0.3), 2)
else:
    confidence = 0.0

# If keyword matching is inconclusive, use LLM classification
if confidence < 0.60:
    classify_query = f"""
    SELECT SNOWFLAKE.CORTEX.COMPLETE(
        'claude-haiku-4-5',
        'Classify the following text into exactly one category. Return ONLY the category name, nothing else.
Categories:
- fraud-query (about transaction risk, fraud signals, suspicious activity, account risk)
- regulation-query (about policies, compliance, AML/KYC/BSA rules, legal requirements)
- report-request (about generating SAR reports, audit findings, investigation summaries)
- verification-status-query (about customer verification status, confirmation responses, dispatch status)

Text: {intent_text.replace("'", "''")}'
    ) AS classification
    """
    try:
        llm_result = _snowflake.execute_sql(classify_query)
        if llm_result and llm_result[0]['CLASSIFICATION']:
            llm_class = llm_result[0]['CLASSIFICATION'].strip().lower()
            for intent_key in INTENT_PATTERNS.keys():
                if intent_key in llm_class:
                    best_intent = intent_key
                    confidence = 0.80
                    break
    except Exception:
        pass  # Fall back to keyword-based classification

# Build skill parameters based on classified intent
skill_name = INTENT_PATTERNS[best_intent]["skill"]
skill_parameters = {}

if best_intent == "fraud-query":
    # Extract account_id if mentioned
    acc_match = re.search(r'(ACC-\d+)', intent_text, re.IGNORECASE)
    skill_parameters = {
        "account_id": acc_match.group(1) if acc_match else "<requires_account_id>",
        "timeframe_hours": 24
    }
elif best_intent == "regulation-query":
    # Extract jurisdiction if mentioned
    jurisdictions = ["US", "EU", "UK", "DE", "FR", "SG", "AU", "GLOBAL"]
    found_jurisdiction = "ALL"
    for j in jurisdictions:
        if j.lower() in intent_text_lower:
            found_jurisdiction = j
            break
    skill_parameters = {
        "question": intent_text,
        "jurisdiction": found_jurisdiction
    }
elif best_intent == "report-request":
    skill_parameters = {
        "case_id": case_id if case_id else "<requires_case_id>"
    }
elif best_intent == "verification-status-query":
    skill_parameters = {
        "case_id": case_id if case_id else "<requires_case_id>"
    }

# Determine if clarification is needed
requires_clarification = confidence < 0.60
clarification_prompt = None
if requires_clarification:
    clarification_prompt = (
        "I'm not fully sure how to route your request. Could you clarify whether you're asking about: "
        "(1) fraud signals on a transaction, "
        "(2) a regulatory/compliance policy question, "
        "(3) generating an audit/SAR report, or "
        "(4) checking a customer verification status?"
    )

# Detect compound intents (multiple categories with significant scores)
compound_intents = []
for intent_key, config in INTENT_PATTERNS.items():
    if config["weight"] > 0:
        compound_intents.append({
            "intent": intent_key,
            "skill": config["skill"],
            "weight": config["weight"]
        })
compound_intents.sort(key=lambda x: x["weight"], reverse=True)
is_compound = len(compound_intents) > 1

# Build reasoning
reasoning_parts = []
if INTENT_PATTERNS[best_intent]["weight"] > 0:
    matched_kws = [kw for kw in INTENT_PATTERNS[best_intent]["keywords"] if kw in intent_text_lower]
    reasoning_parts.append(f"Matched keywords: {', '.join(matched_kws[:5])}")
reasoning_parts.append(f"Classification confidence: {confidence}")
if is_compound:
    reasoning_parts.append(f"Compound query detected: {len(compound_intents)} intents identified")
reasoning = ". ".join(reasoning_parts)

output = {
    "classified_intent": best_intent,
    "confidence": confidence,
    "routed_skill": skill_name,
    "skill_parameters": skill_parameters,
    "requires_clarification": requires_clarification,
    "clarification_prompt": clarification_prompt,
    "is_compound": is_compound,
    "compound_intents": compound_intents if is_compound else None,
    "reasoning": reasoning
}

print(json.dumps(output, indent=2))
