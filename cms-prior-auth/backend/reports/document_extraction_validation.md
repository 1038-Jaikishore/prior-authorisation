# Clinical Document Extraction & Validation Specification

This document details the Pydantic schema schemas, validation metrics, and safety rules that govern the LLM clinical fact extraction layer.

## 1. Pydantic Structured Schema
All raw document extractions map strictly to the `ExtractedClinicalDocument` model:
* **PatientDemographics**: Name, DOB, Age, Gender.
* **RequestedService**: Code, Code System (CPT/HCPCS), Description.
* **Diagnoses (ICD-10-CM)**: Codes, descriptions, and onset dates.
* **PriorTreatments**: Treatment type (medication, surgery, physical therapy), name, duration, and failure status.
* **DiagnosticResults**: Lab tests, results, and dates.
* **Geography**: State code and ZIP code.
* **ProvenanceRecords**: Mappings showing page numbers and exact matched text snippets.

## 2. Validation & Safety Constraints
To enforce clinical safety, the service enforces the following strict rules:
* **Zero Medical Guessing**: No inference of code values is allowed. If a code is not explicitly present in the text, it is flagged as `NOT_DOCUMENTED` (remains null).
* **Null Value Retention**: If fields are missing in the raw text, they must map to `None` in the Pydantic structure rather than default placeholders.
* **No Code Modification**: If an ICD-10 or HCPCS code is documented, it is parsed and stored exactly as-is without any normalization or translation.
