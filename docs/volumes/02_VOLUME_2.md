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

# Volume 2 --- Normalization, MongoDB Atlas Schema & Ingestion

## Goal

Transform audited CMS sources into stable normalized documents and load
them safely into a dedicated MongoDB Atlas database.

## Database isolation

Use a dedicated database name such as `cms_prior_auth`. Never use
`dropDatabase()` against another database and never delete unrelated
collections.

## Proposed collections

Start from the Volume 1 data dictionary and adjust only when actual
schemas justify it: - `ncds` - `lcds` - `articles` -
`lcd_article_relationships` - `lcd_ncd_relationships` -
`article_ncd_relationships` - `hcpcs_codes` - `lcd_hcpcs` -
`article_hcpcs` - `hcpcs_groups` - `article_modifiers` -
`icd10cm_article_covered` - `icd10cm_article_noncovered` -
`icd10pcs_codes` - `bill_codes` - `revenue_codes` - `contractors` -
`lcd_jurisdictions` - `article_jurisdictions` - `related_documents` -
`revision_history` - `coding_information` - `ingestion_runs`

Do not create unnecessary duplicate collections when two source files
represent the same logical entity; document consolidation decisions.

## Document requirements

Every normalized CMS document should preserve: - canonical IDs -
original/source IDs where useful - effective/revision/termination dates
when available - status - source file - source row or source record
identifier - ingestion run ID - normalization version

## Tasks

1.  Implement MongoDB connection through `MONGODB_URI` and `MONGODB_DB`.
2.  Never print credentials.
3.  Add startup health check.
4.  Build normalization modules per source family.
5.  Write normalized output to `backend/data/normalized/` for inspection
    before upload.
6.  Build idempotent ingestion/upsert scripts.
7.  Create indexes for common joins/lookups:
    -   NCD ID
    -   LCD ID
    -   Article ID
    -   HCPCS code
    -   ICD code
    -   contractor/jurisdiction
    -   effective/status fields where appropriate
8.  Add unique compound indexes only when the audit proves uniqueness.
9.  Add referential-integrity reports after ingestion.
10. Record ingestion counts and rejected rows in `ingestion_runs`.
11. Add API `/health/db` and internal repository methods.
12. Add tests using mocks/test database configuration.

## Safety requirements

-   No destructive database commands by default.
-   A cleanup script may delete only collections in `cms_prior_auth` and
    must require an explicit flag.
-   Never touch other Atlas databases.
-   Raw source files remain unchanged.

## Completion gate

-   Expected normalized records equal inserted/upserted + rejected
    records.
-   Key lookup tests work for NCD/LCD/Article/HCPCS.
-   Relationship joins have measured match rates.
-   Re-running ingestion does not duplicate records.

## Antigravity execution prompt

Implement only Volume 2 using the Volume 1 audit as the source of truth.
Create normalized datasets, MongoDB Atlas models/repositories, safe
idempotent ingestion, indexes and validation reports. Use only
environment variables for secrets. Never delete unrelated databases or
collections. Run ingestion validation and tests, fix errors, and stop
after producing a Volume 2 completion report.
