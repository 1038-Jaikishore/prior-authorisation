# Document Evidence Mapping & Provenance Specification

This report outlines the clinical evidence merge mechanism, conflict flagging rules, and provenance tracking specifications.

## 1. Multi-source Merge Logic
When compiling the `ClinicalEvidencePacket`, the `PriorAuthorizationIntakeService` queries all confirmed document extractions linked to the authorization request:
* Extracted conditions are appended to the packet `conditions` list with `source: "EXTRACTED_FROM_DOCUMENT"`.
* Extracted medications and surgeries are appended to the corresponding lists and compiled into the packet `prior_treatments` list.
* Extracted diagnostic results are appended to the `diagnostic_results` list.

## 2. Evidence Conflict Checkers
The compiler runs automated validations to flag contradictions:
* **DOB Conflict**: If the structured database patient date of birth differs from the extracted document date of birth, it appends a `CONFLICTING_DOCUMENT_EVIDENCE: Structured DOB conflicts with uploaded document DOB` warning.
* **Surgical Conflict**: If the narrative provider history states "no previous surgeries" but the uploaded clinical document contains surgical history, a `CONFLICTING_DOCUMENT_EVIDENCE` warning is added to the packet's warnings list.

## 3. Provenance & Audit Mappings
Every fact extracted from the document preserves its source location:
* A `provenance` record is generated with:
  - `fact_type`: Field reference (e.g. `diagnosis_code`).
  - `value`: Mapped code or string value.
  - `source_collection`: `"patient_documents"`.
  - `source_record_id`: Document ID.
  - `source_field`: Page number and source snippet preview (e.g. `page 1: Osteoarthritis M17.11`).
* This ensures auditability and human review trace transparency.
