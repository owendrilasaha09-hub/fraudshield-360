import json
import re
import _snowflake

# Parameters injected by the skill runtime
question = question  # noqa: F841
jurisdiction = jurisdiction if 'jurisdiction' in dir() else 'ALL'  # noqa: F841

# --- Input validation ---
if not isinstance(question, str) or len(question.strip()) == 0:
    print(json.dumps({"error": "question is required"}))
    raise SystemExit(0)
question = question[:1000]

if not isinstance(jurisdiction, str) or not re.match(r'^[A-Za-z]{1,10}$', jurisdiction):
    jurisdiction = 'ALL'

# Query the Cortex Search Service
search_query = f"""
SELECT
    chunk_text,
    source_document,
    page_number,
    SCORE AS confidence_score
FROM TABLE(
    FRAUDSHIELD_360_DB.DOCUMENTS.REGULATORY_SEARCH_SVC!SEARCH(
        QUERY => '{question.replace("'", "''")}',
        COLUMNS => ['chunk_text', 'source_document', 'page_number'],
        LIMIT => 3
    )
)
ORDER BY confidence_score DESC
LIMIT 1
"""

result = _snowflake.execute_sql(search_query)
row = result[0] if result else None

CONFIDENCE_THRESHOLD = 0.70

if row is None:
    output = {
        "answer_text": "Insufficient evidence in policy documents.",
        "source_document": None,
        "page_number": None,
        "confidence_score": 0.0
    }
else:
    confidence_score = float(row['CONFIDENCE_SCORE']) if row['CONFIDENCE_SCORE'] else 0.0
    source_document = row['SOURCE_DOCUMENT']
    page_number = int(row['PAGE_NUMBER']) if row['PAGE_NUMBER'] else None
    chunk_text = row['CHUNK_TEXT']

    # Apply confidence guardrail
    if confidence_score < CONFIDENCE_THRESHOLD:
        answer_text = "Insufficient evidence in policy documents."
    else:
        # Generate answer grounded in retrieved context
        # Use AI_COMPLETE to synthesize an answer from the chunk
        answer_query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'claude-sonnet-4-5',
            CONCAT(
                'You are a regulatory compliance assistant. Answer the following question using ONLY the provided document context. ',
                'Do not add information beyond what is stated in the context. If the context does not fully answer the question, say so. ',
                'Be concise and precise.\\n\\n',
                'CONTEXT (from {source_document.replace("'", "''")} page {page_number}):\\n',
                '{chunk_text.replace("'", "''")}\\n\\n',
                'QUESTION: {question.replace("'", "''")}\\n\\n',
                'ANSWER:'
            )
        ) AS answer
        """
        answer_result = _snowflake.execute_sql(answer_query)
        if answer_result and answer_result[0]['ANSWER']:
            answer_text = answer_result[0]['ANSWER'].strip()
        else:
            answer_text = chunk_text[:500]

    output = {
        "answer_text": answer_text,
        "source_document": source_document,
        "page_number": page_number,
        "confidence_score": round(confidence_score, 4)
    }

print(json.dumps(output, indent=2))
