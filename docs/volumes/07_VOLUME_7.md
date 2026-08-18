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
