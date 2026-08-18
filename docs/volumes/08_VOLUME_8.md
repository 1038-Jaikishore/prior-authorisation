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
