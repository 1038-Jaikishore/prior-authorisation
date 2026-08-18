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
