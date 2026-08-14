# CMS Prior Authorization --- Antigravity Build Plan

> **Scope:** U.S. Medicare/CMS prior-authorization decision-support
> prototype.
>
> **Core principle:** LLMs explain and extract; structured CMS data and
> deterministic rules perform code/policy validation. The system must
> preserve provenance and should not present itself as an autonomous
> final coverage authority.

## Target stack

-   Frontend: React/TypeScript
-   Backend: FastAPI/Python
-   Structured database: MongoDB Atlas
-   RAG: MongoDB Atlas Vector Search
-   LLM: provider abstraction (OpenRouter during development;
    OpenAI-compatible provider later)
-   Configuration/secrets: `.env`, never hard-coded
-   Tests: pytest
-   Source control: Git; `.env` and generated/private data excluded

## CMS source families already available

The project has 27 CMS/reference files covering NCDs, LCDs, Articles,
LCD↔Article and NCD relationships, HCPCS mappings/groups/modifiers,
ICD-10 covered/noncovered Article mappings, ICD-10-PCS, ICD-10-CM
tabular reference, contractors/jurisdictions, revenue codes, bill codes,
revision history and related documents.

## Non-negotiable engineering rules

1.  Never modify the original source files in place.
2.  Keep raw, normalized and derived data distinguishable.
3.  Preserve CMS IDs, effective/revision dates, source file and source
    row/provenance.
4.  Do not embed every CSV row. Vectorize narrative policy text only.
5.  Use structured mappings before semantic retrieval.
6.  NCD routing/evaluation precedes LCD fallback where applicable.
7.  Geographic LCD selection must use jurisdiction/MAC information.
8.  Article coding guidance is related to, but not identical with, LCD
    medical-necessity policy.
9.  Every decision factor must be traceable to patient evidence,
    deterministic validation, or a policy citation.
10. Missing/ambiguous evidence should route to PEND/NURSE REVIEW rather
    than being hallucinated.

# Volume 1 --- Foundation, Dataset Audit & Data Contract

## Goal

Create a reproducible project foundation and inspect all 27 source files
before any production ingestion.

## Inputs

Use the files under `backend/data/cms_data/`. Treat them as read-only
source assets.

Expected source families include: - NCD: `ncd_documents_data.csv` - LCD:
`lcd_documents.csv`, `lcd_full_data.csv`,
`lcd_master_excel_safe.csv.xlsx`, `lcd_revision_history.csv`,
`lcd_contractor.csv`, `cms_lcd_primary_jurisdiction.csv.xls`, LCD
related-document/NCD files - Articles: `articles_700.csv`,
`lcd_article_relationship.csv`, `article_related_lcds.csv`,
`article_related_ncd_documents_data.csv`, `article_bill_codes.csv`,
`cms_article_jurisdiction.csv.xls` - HCPCS: `CMS_HCPC_code.csv`,
LCD/Article HCPCS mappings and code-group files, modifier files - ICD:
`icd10_covered_all_articles.csv`, `icd10_noncovered_all_articles.csv`,
`icd10_pcs_codes.csv`, `icd10cm_tabular_2027.pdf` - Other coding:
`revenue_codes.csv`, `CMS_Other_Coding_Information_All_Articles.csv`

## Tasks for Antigravity

1.  Create the backend skeleton:
    -   `backend/app/`
    -   `backend/app/core/`
    -   `backend/app/db/`
    -   `backend/app/models/`
    -   `backend/app/services/`
    -   `backend/app/rag/`
    -   `backend/app/validators/`
    -   `backend/app/api/`
    -   `backend/scripts/`
    -   `backend/tests/`
    -   `backend/data/cms_data/`
    -   `backend/data/normalized/`
    -   `backend/reports/`
2.  Add configuration using environment variables.
3.  Build `scripts/audit_cms_datasets.py`.
4.  Detect actual file format by content, not extension. Some `.xls`
    files may actually contain delimited text.
5.  For every file report:
    -   physical format and encoding
    -   row/column count
    -   exact column names
    -   inferred types
    -   null counts
    -   duplicate counts
    -   candidate primary/business keys
    -   sample values
    -   malformed rows
    -   date fields and formats
    -   HTML/markup presence
6.  Explicitly detect accidental header problems in code files.
7.  Build a relationship/key report for NCD, LCD, Article, HCPCS, ICD,
    contractor, jurisdiction, bill code, modifier and revenue-code
    identifiers.
8.  Generate:
    -   `backend/reports/dataset_audit.md`
    -   `backend/reports/data_dictionary.json`
    -   `backend/reports/relationship_report.md`
    -   `backend/reports/data_quality_report.json`
9.  Add unit tests for format detection and key normalization.
10. Do **not** connect to MongoDB and do **not** mutate raw files.

## Normalization contract to propose

Define canonical representations for: - `ncd_id` - `lcd_id` -
`article_id` - `hcpcs_code` - `icd10cm_code` - `icd10pcs_code` -
`modifier_code` - `revenue_code` - `bill_type_code` - contractor/MAC
identifier - jurisdiction - dates

IDs should normally be stored as strings so leading zeros/formatting are
never lost.

## Required completion gate

Volume 1 is complete only when all 27 files are represented in the audit
and every relationship file has identified join keys or is explicitly
flagged unresolved.

## Antigravity execution prompt

Read this Volume 1 specification completely. Work only on Volume 1.
Inspect the actual files rather than assuming schemas from filenames. Do
not modify raw datasets, do not connect to MongoDB, and do not start
later volumes. Run tests and the audit script. Fix errors you introduce.
At completion, summarize files created, all detected source schemas,
unresolved data-quality issues, relationship keys, and exact commands
used.
