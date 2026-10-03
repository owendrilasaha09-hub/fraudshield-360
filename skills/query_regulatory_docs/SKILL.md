# query_regulatory_docs

## name
query_regulatory_docs

## description
Queries the REGULATORY_SEARCH_SVC Cortex Search Service to answer regulatory compliance questions grounded in uploaded policy documents. Returns a structured response with the answer, source document, page number, and confidence score. Enforces a confidence guardrail: answers below 0.70 confidence are replaced with a disclaimer.

## instructions

You are a regulatory document retrieval skill. When invoked, execute the `query_regulatory_docs.py` script to search regulatory documents and answer compliance questions.

### Parameters

- **question** (VARCHAR, required): The regulatory or compliance question to answer (e.g., "What are the KYC requirements for high-risk customers?").
- **jurisdiction** (VARCHAR, required): The jurisdiction to filter results by (e.g., "US", "EU", "UK", "GLOBAL"). If unknown, pass "ALL".

### Behavior

1. Query the Cortex Search Service `FRAUDSHIELD_360_DB.DOCUMENTS.REGULATORY_SEARCH_SVC` with the user's question.
2. Filter results by jurisdiction if a `source_document` column contains jurisdiction metadata.
3. Use the top result's relevance score as the confidence_score.
4. Generate an `answer_text` grounded ONLY in the retrieved chunk_text context. Do not hallucinate or infer beyond what the document states.
5. **GUARDRAIL**: If confidence_score < 0.70, override answer_text with exactly: "Insufficient evidence in policy documents."
6. Return the source_document filename and page_number from the top matching chunk.

### Output Schema (JSON)

```json
{
  "answer_text": "<answer grounded in retrieved context, or guardrail message>",
  "source_document": "<PDF filename>",
  "page_number": <integer>,
  "confidence_score": <float between 0.0 and 1.0>
}
```

### Example Invocation

"What does the AML policy say about transaction monitoring thresholds in the EU?"

Run the script with:
- question = "What does the AML policy say about transaction monitoring thresholds?"
- jurisdiction = "EU"

### Guardrail

If the confidence_score returned by the search service is below 0.70, the skill MUST return:
```json
{
  "answer_text": "Insufficient evidence in policy documents.",
  "source_document": "<best match document or null>",
  "page_number": <best match page or null>,
  "confidence_score": <actual score>
}
```

### Execution

Run the following SQL query using the `sql_execute` tool, replacing `{question}` (escape single quotes) and `{jurisdiction}`:

```sql
SELECT chunk_text, source_document, page_number, SCORE AS confidence_score
FROM TABLE(
    FRAUDSHIELD_360_DB.DOCUMENTS.REGULATORY_SEARCH_SVC!SEARCH(
        QUERY => '{question}',
        COLUMNS => ['chunk_text', 'source_document', 'page_number'],
        LIMIT => 3
    )
)
ORDER BY confidence_score DESC
LIMIT 1
```

If the confidence_score >= 0.70, synthesize an answer from the chunk_text. If below 0.70 or no results, respond with: "Insufficient evidence in policy documents."
