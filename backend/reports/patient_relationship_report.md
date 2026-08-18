# Patient Relationship Join Report

This report details the integrity of joins linking child tables back to parent tables (`patients` and `providers`).

| Filename | Join Key | Target Table | Match Count | Total Rows | Match Rate | Broken Refs Count |
| --- | --- | --- | --- | --- | --- | --- |
| `allergies.csv` | `patient_id` | `patients.csv` | 40 | 40 | 100.0% | 0 |
| `authorization_requests.csv` | `patient_id` | `patients.csv` | 50 | 50 | 100.0% | 0 |
| `authorization_requests.csv` | `provider_id` | `providers.csv` | 50 | 50 | 100.0% | 0 |
| `care_plans.csv` | `patient_id` | `patients.csv` | 40 | 40 | 100.0% | 0 |
| `care_plans.csv` | `provider_id` | `providers.csv` | 40 | 40 | 100.0% | 0 |
| `claims.csv` | `patient_id` | `patients.csv` | 100 | 100 | 100.0% | 0 |
| `claims.csv` | `provider_id` | `providers.csv` | 100 | 100 | 100.0% | 0 |
| `clinical_assessments.csv` | `patient_id` | `patients.csv` | 60 | 60 | 100.0% | 0 |
| `conditions.csv` | `patient_id` | `patients.csv` | 80 | 80 | 100.0% | 0 |
| `coverage.csv` | `patient_id` | `patients.csv` | 30 | 30 | 100.0% | 0 |
| `diagnostic_results.csv` | `patient_id` | `patients.csv` | 80 | 80 | 100.0% | 0 |
| `encounters.csv` | `patient_id` | `patients.csv` | 80 | 80 | 100.0% | 0 |
| `encounters.csv` | `provider_id` | `providers.csv` | 80 | 80 | 100.0% | 0 |
| `family_history.csv` | `patient_id` | `patients.csv` | 40 | 40 | 100.0% | 0 |
| `functional_status.csv` | `patient_id` | `patients.csv` | 60 | 60 | 100.0% | 0 |
| `immunizations.csv` | `patient_id` | `patients.csv` | 60 | 60 | 100.0% | 0 |
| `medical_equipment.csv` | `patient_id` | `patients.csv` | 40 | 40 | 100.0% | 0 |
| `medications.csv` | `patient_id` | `patients.csv` | 100 | 100 | 100.0% | 0 |
| `procedures.csv` | `patient_id` | `patients.csv` | 60 | 60 | 100.0% | 0 |
| `procedures.csv` | `provider_id` | `providers.csv` | 60 | 60 | 100.0% | 0 |
| `providers.csv` | `provider_id` | `providers.csv` | 15 | 15 | 100.0% | 0 |
| `referrals.csv` | `patient_id` | `patients.csv` | 50 | 50 | 100.0% | 0 |
| `social_history.csv` | `patient_id` | `patients.csv` | 30 | 30 | 100.0% | 0 |
| `surgeries.csv` | `patient_id` | `patients.csv` | 50 | 50 | 100.0% | 0 |
| `surgeries.csv` | `provider_id` | `providers.csv` | 50 | 50 | 100.0% | 0 |
| `vital_signs.csv` | `patient_id` | `patients.csv` | 100 | 100 | 100.0% | 0 |

## Broken References Detail (Sample display)
