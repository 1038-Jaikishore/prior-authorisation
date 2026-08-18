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
