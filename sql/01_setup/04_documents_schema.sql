-- ============================================================================
-- FraudShield 360 - DOCUMENTS Schema (RAG Infrastructure)
-- ============================================================================

USE DATABASE FRAUDSHIELD_360_DB;
USE SCHEMA DOCUMENTS;

-- Internal stage for regulatory PDFs
CREATE STAGE IF NOT EXISTS REGULATORY_DOCS
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Internal stage for regulatory PDF documents used in RAG pipeline';

-- Document chunks table
CREATE TABLE IF NOT EXISTS DOCUMENT_CHUNKS (
    CHUNK_ID VARCHAR NOT NULL PRIMARY KEY,
    SOURCE_DOCUMENT VARCHAR,
    CHUNK_TEXT VARCHAR,
    PAGE_NUMBER INT
);

-- Cortex Search Service
CREATE OR REPLACE CORTEX SEARCH SERVICE REGULATORY_SEARCH_SVC
  ON chunk_text
  ATTRIBUTES source_document, page_number
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
  COMMENT = 'Cortex Search service for regulatory document RAG lookups'
AS (
  SELECT chunk_id, source_document, chunk_text, page_number
  FROM DOCUMENT_CHUNKS
);
