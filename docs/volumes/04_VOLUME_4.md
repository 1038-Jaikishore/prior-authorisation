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
