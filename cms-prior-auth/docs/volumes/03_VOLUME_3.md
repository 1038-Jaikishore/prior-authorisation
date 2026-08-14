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
