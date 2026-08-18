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

# End-to-End Architecture

``` text
Prior Authorization Request
        ↓
Clinical extraction + normalization
        ↓
Structured CMS policy routing
        ↓
NCD evaluation
   ┌────┼─────────┐
covered excluded not-addressed
   │       │          ↓
   │       │      LCD + jurisdiction/MAC
   │       │          ↓
   │       │      related Article(s)
   └───────┴──────────┐
                      ↓
Restricted policy RAG
                      ↓
Requirement extraction
                      ↓
Patient evidence matching
              +
Deterministic coding validation
                      ↓
Versioned triage/decision engine
                      ↓
APPROVE / DENY / PEND / NURSE REVIEW
                      ↓
LLM explanation + citations
                      ↓
Human reviewer + audit trail
```

# Volume Order

1.  Foundation, dataset audit & data contract
2.  Normalization, MongoDB Atlas schema & ingestion
3.  CMS policy routing & hierarchy resolution
4.  NCD/LCD/Article RAG with Atlas Vector Search
5.  Patient & prior-authorization intake
6.  Evidence matching & deterministic validation
7.  Confidence, triage & decision recommendation
8.  LLM explanation, citations, reviewer UI & end-to-end demo

# Cross-Volume Stop Rule

Antigravity must complete, test and report the current volume before
starting the next one. A later volume may consume prior outputs but
should not silently redesign earlier data contracts. If a blocking
schema problem is discovered, document it and make the smallest
backward-compatible correction.

# Data Still Needed

The CMS policy/coding corpus is sufficient to start Volumes 1--4. Before
Volume 5 is finalized, provide the synthetic patient/prior-authorization
data (or approve a canonical synthetic JSON schema). If
provider/facility and ZIP/state jurisdiction resolution are not present
in that patient/request data, provide or generate synthetic fields for
them.

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

# Volume 3 --- CMS Policy Routing & Hierarchy Resolution

## Goal

Given a normalized prior-auth service context, deterministically
identify candidate/applicable CMS coverage documents before RAG.

## Input contract

Design a `PolicyRoutingRequest` containing, as available: - HCPCS/CPT
code - diagnosis ICD-10-CM codes - ICD-10-PCS if applicable -
modifier(s) - revenue/bill codes - state/ZIP/location - date of
service - provider/facility context

## Routing sequence

1.  Normalize codes.
2.  Validate basic code existence.
3.  Use structured HCPCS mappings to identify policy candidates.
4.  Resolve applicable NCD candidates.
5.  Determine whether a controlling national determination addresses the
    service.
6.  When local evaluation is needed, resolve
    jurisdiction/MAC/contractor.
7.  Filter candidate LCDs by service, geography, status and date.
8.  Resolve related Article(s).
9.  Return a trace explaining every routing step.

## Important behavior

-   Do not semantic-search the entire policy corpus to determine
    jurisdiction.
-   Do not let an LCD override an explicit controlling NCD exclusion.
-   Do not equate "no NCD found" with "covered."
-   Multiple candidate policies should be returned as ambiguity, not
    silently collapsed.
-   Date-of-service applicability must be preserved when source data
    supports it.

## Output contract

Return: - normalized request - candidate NCDs - NCD routing status -
MAC/contractor/jurisdiction resolution - candidate/applicable LCDs -
related Articles - structured mappings used - unresolved/ambiguous
fields - routing trace - confidence in routing (not coverage)

## API

Add endpoints such as: - `POST /api/policy/route` -
`GET /api/policy/ncd/{id}` - `GET /api/policy/lcd/{id}` -
`GET /api/policy/article/{id}`

## Tests

Create fixture cases for: - NCD found - explicit NCD exclusion metadata
if available - no national determination → local route - multiple LCD
candidates - missing geography - invalid HCPCS -
inactive/date-mismatched policy - related Article resolution

## Completion gate

Policy routing works without an LLM and produces a fully inspectable
trace.

## Antigravity execution prompt

Implement only Volume 3. Build a deterministic CMS policy router using
the structured MongoDB relationships created in Volume 2. Do not build
RAG or a decision engine yet. Every routing result must show which
records and mappings caused it. Add API endpoints, fixtures and tests,
fix errors, and stop with a routing validation report.

# Volume 4 --- NCD/LCD/Article RAG with Atlas Vector Search

## Goal

Retrieve precise policy passages only after structured policy routing
has narrowed the relevant documents.

## What to embed

Embed narrative text from: - NCD
coverage/indications/limitations/denial-reason sections - LCD
coverage/medical-necessity/limitations/evidence/coding narrative
sections - Article narrative/coding guidance sections

Do not vectorize simple lookup tables such as raw HCPCS, ICD mappings,
modifiers, revenue codes or jurisdiction tables.

## `policy_chunks` document

Include: - `chunk_id` - `document_type`: NCD/LCD/ARTICLE -
`document_id` - title - section name - chunk text - embedding - chunk
order - effective/status metadata - contractor/jurisdiction where
applicable - related LCD/NCD IDs when applicable - source/provenance
metadata

## Chunking

-   Chunk by semantic/policy section before token-size splitting.
-   Preserve headings.
-   Avoid mixing sections from different policies.
-   Add overlap only where useful.
-   Never lose document/section identity.

## Retrieval

1.  Receive applicable policy IDs from Volume 3.
2.  Apply metadata filter to those IDs.
3.  Run vector similarity within that restricted set.
4.  Optionally combine lexical/exact section matching.
5.  Return text plus document/section metadata.
6.  Do not generate a coverage decision.

## Embedding abstraction

Create a provider interface so embeddings can be changed without
rewriting retrieval logic. Keep API keys in `.env`.

## Evaluation

Build a small retrieval evaluation set containing representative queries
and expected policy IDs/sections. Report recall@k and obvious failure
cases.

## Completion gate

A query routed to a known LCD/NCD retrieves relevant sections from that
policy and cannot accidentally retrieve an unrelated policy merely
because wording is similar.

## Antigravity execution prompt

Implement only Volume 4. Build section-aware policy chunking,
embeddings, Atlas Vector Search indexing/retrieval and retrieval
evaluation. Retrieval must be constrained by the structured policy IDs
from Volume 3. Do not make approval/denial decisions. Run
indexing/tests, fix errors, and stop with retrieval metrics and sample
cited results.

# Volume 5 --- Patient & Prior-Authorization Intake

## Goal

Create the patient/request side of the system and convert submitted
clinical information into a structured evidence packet.

## Additional data needed at this stage

Before final implementation, provide either: - the synthetic
patient/prior-auth datasets already prepared (e.g., Synthea-style CSVs
plus authorization requests), or - an agreed JSON request schema and
synthetic fixtures.

No real patient PHI is required for the prototype. Prefer
synthetic/de-identified data.

## Core entities

-   patient
-   encounter
-   condition/diagnosis
-   procedure
-   medication
-   diagnostic result
-   vital/assessment where relevant
-   provider/facility
-   prior authorization request
-   supporting clinical note/document

## Intake output

Produce a `ClinicalEvidencePacket`: - patient/request IDs - requested
service - normalized codes - demographics relevant to policy -
diagnoses - symptoms/duration - prior treatments -
diagnostic/imaging/lab evidence - contraindications/comorbidities if
explicitly documented - provider/location/date - provenance for every
fact - missing/uncertain facts

## LLM use

An LLM may extract candidate facts from free text, but: - retain source
spans/provenance - distinguish extracted vs structured facts - never
invent missing evidence - validate codes deterministically afterward -
use structured patient data directly when available

## API

-   `POST /api/prior-auth`
-   `GET /api/prior-auth/{id}`
-   `POST /api/prior-auth/{id}/extract`
-   optional synthetic demo endpoint

## Completion gate

A synthetic request can be transformed into a reproducible evidence
packet with provenance and normalized codes.

## Antigravity execution prompt

Implement only Volume 5 after the synthetic patient/prior-auth data or
final request schema is available. Build patient/request models,
ingestion/intake, clinical extraction and provenance-preserving evidence
packets. Do not make a final coverage decision. Never fabricate missing
clinical facts. Add tests and stop with sample evidence packets and a
completion report.

# Volume 6 --- Evidence Matching & Deterministic Coding Validation

## Goal

Compare patient evidence against retrieved policy requirements while
independently validating administrative/coding rules.

## A. Policy requirement extraction

From the routed/retrieved NCD/LCD/Article sections, create structured
requirements: - requirement ID - policy/document/section - requirement
text - type - required/conditional - normalized code constraints where
applicable

Use deterministic parsing where feasible; LLM extraction must output
structured JSON and retain source citations.

## B. Evidence matching

For each requirement return: - `MET` - `NOT_MET` - `UNCLEAR` -
`NOT_APPLICABLE` plus: - patient evidence references - policy citation -
rationale - missing information

Do not convert absence of evidence into NOT_MET unless the requirement
logically permits that conclusion.

## C. Deterministic validators

Implement validators for available source data: - ICD-10-CM
existence/normalization - ICD-10-PCS existence where applicable - HCPCS
existence - LCD↔HCPCS applicability - Article↔HCPCS applicability -
covered/noncovered Article ICD mappings - modifiers/groups - revenue
codes - bill codes - jurisdiction/contractor applicability -
effective/status/date checks - coding dependencies from structured
source data

The ICD-10-CM tabular reference includes coding conventions such as
Excludes notes and sequencing instructions; implement only rules that
can be reliably parsed/represented, and flag unsupported narrative
conventions rather than guessing.

## Output

`EvaluationBundle`: - policy requirements - evidence matches - coding
validation results - hard failures - warnings - missing information -
citations/provenance

## Completion gate

The same request always produces the same deterministic validation
results, and each policy requirement has an explicit evidence status.

## Antigravity execution prompt

Implement only Volume 6. Build structured policy requirement extraction,
evidence matching and deterministic code/administrative validators using
the CMS collections. Keep evidence matching separate from coding
validation. Never infer undocumented clinical evidence. Add extensive
unit tests for pass/fail/unclear cases, fix errors, and stop with a
validation report.

# Volume 7 --- Confidence, Triage & Decision Recommendation Engine

## Goal

Aggregate policy evaluation, evidence matching and deterministic
validation into a transparent recommendation.

## Output states

-   `APPROVE`
-   `DENY`
-   `PEND`
-   `NURSE_REVIEW`

These are prototype decision-support recommendations, not an assertion
that the software itself is the authoritative Medicare adjudicator.

## Rules

Use explicit, versioned decision rules. Examples of rule categories: -
controlling NCD explicit noncoverage → deny recommendation - required
medical-necessity criterion clearly not met → deny or review according
to rule configuration - all required criteria met + deterministic checks
pass → approve recommendation - required evidence missing → pend -
conflicting policy/evidence or routing ambiguity → nurse review -
unsupported rule interpretation → nurse review

Do not let a numeric confidence score override a hard policy/coding
failure.

## Confidence

Build interpretable components such as: - routing certainty - policy
retrieval quality - requirement extraction completeness - evidence
completeness - deterministic validation completeness -
conflict/ambiguity penalties

Store component scores and the final score. Avoid pretending the score
is a calibrated clinical probability unless it has actually been
validated as such.

## Rule storage

Create versioned rule configuration, e.g. `decision_rules` collection or
versioned config files. Every decision stores the rule version used.

## Explainability payload

Return: - recommendation - confidence score/components - decisive
factors - failed checks - unmet/unclear requirements - missing
information - escalation reason - policy IDs/citations - rule version

## Completion gate

Golden test cases produce stable recommendations and every
recommendation can be reconstructed from stored inputs and rule version.

## Antigravity execution prompt

Implement only Volume 7. Create a deterministic, versioned
triage/decision recommendation engine over the Volume 6 evaluation
bundle. Hard rules must take precedence over confidence. Add golden test
cases for APPROVE, DENY, PEND and NURSE_REVIEW, fix errors, and stop
with a rule matrix and test report.

# Volume 8 --- LLM Explanation, Citations, Reviewer UI & End-to-End Demo

## Goal

Turn the structured recommendation into a concise human-review
experience without allowing the LLM to alter the underlying decision.

## LLM synthesis input

Give the LLM only: - structured recommendation - confidence components -
matched/unmatched requirements - deterministic validation results -
patient evidence snippets - retrieved policy passages/citations -
missing information - next-step rules

## LLM output

Structured JSON plus display text: - summary - recommendation
explanation - evidence used - unmet/unclear requirements - coding
issues - policy citations - missing information - recommended next steps

The generated explanation must not introduce facts absent from the
supplied context.

## Reviewer UI

Build screens for: 1. Prior-auth request intake 2. Patient/request
summary 3. Policy routing trace 4. NCD/LCD/Article viewer 5.
Requirement-vs-evidence matrix 6. Deterministic validation results 7.
Recommendation/confidence 8. Explanation and citations 9. Human reviewer
action/override with reason 10. Audit trail

## Auditability

Persist: - input request version - policy IDs/versions/dates - retrieved
chunk IDs - validation results - decision rule version - LLM
provider/model identifier - prompt/template version - generated
explanation - reviewer action

## Security/prototype hygiene

-   no secrets in frontend
-   sanitize displayed policy/clinical text
-   basic authentication/role placeholder if needed
-   no real PHI in public demos
-   logs must avoid secrets and unnecessary patient details

## End-to-end demo

Create at least four synthetic scenarios: - approve path -
explicit/noncoverage deny path - missing-information pend path -
ambiguity/conflict nurse-review path

## Completion gate

A reviewer can follow the entire chain from request → policy → evidence
→ deterministic checks → recommendation → citation-backed explanation.

## Antigravity execution prompt

Implement only Volume 8. Build the LLM synthesis layer and reviewer UI
on top of the already-computed structured recommendation. The LLM must
never change the recommendation. Add citation links/identifiers, audit
logging, four synthetic end-to-end scenarios and tests. Fix errors and
produce a final architecture/runbook/demo report.
