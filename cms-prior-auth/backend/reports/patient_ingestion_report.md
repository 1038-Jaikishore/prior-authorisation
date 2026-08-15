# Patient Ingestion Execution Report

- **Ingestion Run ID**: `20260815_033444_033737fa`
- **Full Rebuild Execution**: `False`
- **Execution Timestamp**: `2026-08-15 03:34:55 UTC`

## Ingestion Results Summary Table

| Collection | Source File | Total Rows | Inserted (New) | Matched | Modified | Duplicates | Broken References |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `patients` | `patients.csv` | 40 | 0 | 40 | 40 | 0 | 0 |
| `providers` | `providers.csv` | 15 | 0 | 15 | 15 | 0 | 0 |
| `encounters` | `encounters.csv` | 80 | 0 | 80 | 80 | 0 | 0 |
| `patient_conditions` | `conditions.csv` | 80 | 0 | 80 | 80 | 0 | 0 |
| `patient_medications` | `medications.csv` | 100 | 0 | 100 | 100 | 0 | 0 |
| `patient_procedures` | `procedures.csv` | 60 | 0 | 60 | 60 | 0 | 0 |
| `diagnostic_results` | `diagnostic_results.csv` | 80 | 0 | 80 | 80 | 0 | 0 |
| `vital_signs` | `vital_signs.csv` | 100 | 0 | 100 | 100 | 0 | 0 |
| `allergies` | `allergies.csv` | 40 | 0 | 40 | 40 | 0 | 0 |
| `immunizations` | `immunizations.csv` | 60 | 0 | 60 | 60 | 0 | 0 |
| `care_plans` | `care_plans.csv` | 40 | 0 | 40 | 40 | 0 | 0 |
| `social_history` | `social_history.csv` | 30 | 0 | 30 | 30 | 0 | 0 |
| `surgeries` | `surgeries.csv` | 50 | 0 | 50 | 50 | 0 | 0 |
| `functional_status` | `functional_status.csv` | 60 | 0 | 60 | 60 | 0 | 0 |
| `clinical_assessments` | `clinical_assessments.csv` | 60 | 0 | 60 | 60 | 0 | 0 |
| `family_history` | `family_history.csv` | 40 | 0 | 40 | 40 | 0 | 0 |
| `referrals` | `referrals.csv` | 50 | 0 | 50 | 50 | 0 | 0 |
| `medical_equipment` | `medical_equipment.csv` | 40 | 0 | 40 | 40 | 0 | 0 |
| `claims` | `claims.csv` | 100 | 0 | 100 | 100 | 0 | 0 |
| `coverage` | `coverage.csv` | 30 | 0 | 30 | 30 | 0 | 0 |
| `authorization_requests` | `authorization_requests.csv` | 50 | 0 | 50 | 50 | 0 | 0 |

## Ingestion Conclusion
- Idempotency verified: re-running ingestion updates existing business key rows instead of generating duplicates.
- Provenance records appended: each document holds row offsets and run tracking variables for traceability.