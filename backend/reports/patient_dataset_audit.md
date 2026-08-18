# Patient Dataset Audit Report

This report summarizes the static structure of the 21 patient CSV files.

## Summary Metrics Table

| Filename | Row Count | Col Count | Duplicates | Candidate Key(s) | Has Patient ID | Has Provider ID |
| --- | --- | --- | --- | --- | --- | --- |
| `allergies.csv` | 40 | 8 | 0 | `allergy_id` | Yes | No |
| `authorization_requests.csv` | 50 | 16 | 0 | `request_id, requested_procedure_code, supporting_evidence_url` | Yes | Yes |
| `care_plans.csv` | 40 | 10 | 0 | `plan_id` | Yes | Yes |
| `claims.csv` | 100 | 15 | 0 | `claim_id, procedure_code, amount_billed, amount_paid` | Yes | Yes |
| `clinical_assessments.csv` | 60 | 8 | 0 | `assessment_id` | Yes | No |
| `conditions.csv` | 80 | 8 | 0 | `condition_id, onset_date` | Yes | No |
| `coverage.csv` | 30 | 12 | 0 | `patient_id, plan_id` | Yes | No |
| `diagnostic_results.csv` | 80 | 8 | 0 | `result_id` | Yes | No |
| `encounters.csv` | 80 | 9 | 0 | `encounter_id` | Yes | Yes |
| `family_history.csv` | 40 | 6 | 0 | `history_id` | Yes | No |
| `functional_status.csv` | 60 | 9 | 0 | `status_id` | Yes | No |
| `immunizations.csv` | 60 | 7 | 0 | `immunization_id` | Yes | No |
| `medical_equipment.csv` | 40 | 8 | 0 | `equipment_id` | Yes | No |
| `medications.csv` | 100 | 8 | 0 | `medication_id` | Yes | No |
| `patients.csv` | 40 | 9 | 0 | `patient_id, first_name, last_name, member_id, summary_card_text` | Yes | No |
| `procedures.csv` | 60 | 8 | 0 | `procedure_record_id, procedure_date` | Yes | Yes |
| `providers.csv` | 15 | 9 | 0 | `provider_id, first_name, last_name, npi, contact_number` | No | Yes |
| `referrals.csv` | 50 | 9 | 0 | `referral_id` | Yes | No |
| `social_history.csv` | 30 | 8 | 0 | `social_history_id, patient_id` | Yes | No |
| `surgeries.csv` | 50 | 8 | 0 | `surgery_id` | Yes | Yes |
| `vital_signs.csv` | 100 | 9 | 0 | `vital_id` | Yes | No |

## Detailed Columns & Types

### allergies.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `allergy_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `allergen_type` | `object` | 0 |
| `allergen_name` | `object` | 0 |
| `reaction_severity` | `object` | 0 |
| `onset_date` | `object` | 0 |
| `active_status` | `object` | 0 |
| `conflict_alert_flag` | `bool` | 0 |

### authorization_requests.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `request_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `provider_id` | `object` | 0 |
| `requested_procedure_code` | `object` | 0 |
| `diagnosis_code` | `object` | 0 |
| `clinical_indication` | `object` | 0 |
| `medical_necessity` | `object` | 0 |
| `provider_justification` | `object` | 0 |
| `urgency` | `object` | 0 |
| `requested_quantity` | `int64` | 0 |
| `requested_duration_days` | `int64` | 0 |
| `request_date` | `object` | 0 |
| `status` | `object` | 0 |
| `previous_treatment_info` | `object` | 0 |
| `supporting_evidence_url` | `object` | 0 |
| `ai_reasoning` | `object` | 12 |

### care_plans.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `plan_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `provider_id` | `object` | 0 |
| `current_treatment_plan` | `object` | 0 |
| `planned_procedures` | `object` | 0 |
| `treatment_goals` | `object` | 0 |
| `start_date` | `object` | 0 |
| `end_date` | `object` | 0 |
| `treatments_attempted` | `object` | 13 |
| `status` | `object` | 0 |

### claims.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `claim_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `provider_id` | `object` | 0 |
| `procedure_code` | `object` | 0 |
| `diagnosis_code` | `object` | 0 |
| `claim_status` | `object` | 0 |
| `treatment_date` | `object` | 0 |
| `service_type` | `object` | 0 |
| `treatment_name` | `object` | 0 |
| `amount_billed` | `float64` | 0 |
| `amount_paid` | `float64` | 0 |
| `treatment_frequency` | `int64` | 0 |
| `step_therapy_verified` | `object` | 31 |
| `previous_auth_history` | `object` | 32 |
| `duplicate_service_flag` | `bool` | 0 |

### clinical_assessments.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `assessment_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `assessment_date` | `object` | 0 |
| `assessment_type` | `object` | 0 |
| `score` | `float64` | 0 |
| `severity_level` | `object` | 4 |
| `threshold_met` | `object` | 0 |
| `progression_trend` | `object` | 12 |

### conditions.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `condition_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `diagnosis_code` | `object` | 0 |
| `diagnosis_name` | `object` | 0 |
| `onset_date` | `object` | 0 |
| `resolution_date` | `object` | 45 |
| `condition_type` | `object` | 0 |
| `relevant_to_procedure_flag` | `bool` | 0 |

### coverage.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `patient_id` | `object` | 0 |
| `plan_id` | `object` | 0 |
| `insurance_company` | `object` | 0 |
| `plan_type` | `object` | 0 |
| `effective_date` | `object` | 0 |
| `expiry_date` | `object` | 0 |
| `is_active` | `object` | 0 |
| `requires_prior_auth` | `object` | 0 |
| `benefits_summary` | `object` | 0 |
| `covered_services` | `object` | 0 |
| `copay_amount` | `int64` | 0 |
| `deductible` | `int64` | 0 |

### diagnostic_results.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `result_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `test_name` | `object` | 0 |
| `test_date` | `object` | 0 |
| `result_value` | `object` | 0 |
| `reference_range` | `object` | 0 |
| `abnormal_flag` | `bool` | 0 |
| `evidence_for_medical_necessity` | `bool` | 0 |

### encounters.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `encounter_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `provider_id` | `object` | 0 |
| `encounter_date` | `object` | 0 |
| `encounter_type` | `object` | 0 |
| `primary_diagnosis_code` | `object` | 0 |
| `discharge_status` | `object` | 0 |
| `follow_up_required` | `object` | 0 |
| `recent_hospitalization_flag` | `bool` | 0 |

### family_history.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `history_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `family_member_relation` | `object` | 0 |
| `condition` | `object` | 0 |
| `age_of_onset` | `int64` | 0 |
| `genetic_risk_indicator` | `object` | 0 |

### functional_status.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `status_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `assessment_date` | `object` | 0 |
| `physical_functional_status` | `object` | 0 |
| `mental_functional_status` | `object` | 0 |
| `quality_of_life_score` | `int64` | 0 |
| `deterioration_detected` | `bool` | 0 |
| `pre_post_treatment_flag` | `object` | 0 |
| `rehab_support_needed` | `bool` | 0 |

### immunizations.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `immunization_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `vaccine_name` | `object` | 0 |
| `dose_number` | `int64` | 0 |
| `date_administered` | `object` | 0 |
| `next_due_date` | `object` | 10 |
| `status` | `object` | 0 |

### medical_equipment.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `equipment_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `equipment_type` | `object` | 0 |
| `date_issued` | `object` | 0 |
| `expected_replacement_date` | `object` | 0 |
| `current_status` | `object` | 0 |
| `usage_frequency` | `object` | 0 |
| `duplicate_request_flag` | `bool` | 0 |

### medications.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `medication_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `medication_name` | `object` | 0 |
| `dosage` | `object` | 0 |
| `start_date` | `object` | 0 |
| `end_date` | `object` | 48 |
| `status` | `object` | 0 |
| `step_therapy_requirement_met` | `bool` | 0 |

### patients.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `patient_id` | `object` | 0 |
| `first_name` | `object` | 0 |
| `last_name` | `object` | 0 |
| `dob` | `object` | 0 |
| `age` | `int64` | 0 |
| `gender` | `object` | 0 |
| `insurance_plan` | `object` | 0 |
| `member_id` | `object` | 0 |
| `summary_card_text` | `object` | 0 |

### procedures.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `procedure_record_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `provider_id` | `object` | 0 |
| `procedure_code` | `object` | 0 |
| `procedure_name` | `object` | 0 |
| `procedure_date` | `object` | 0 |
| `outcome` | `object` | 0 |
| `related_to_current_request` | `bool` | 0 |

### providers.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `provider_id` | `object` | 0 |
| `first_name` | `object` | 0 |
| `last_name` | `object` | 0 |
| `specialty` | `object` | 0 |
| `facility_name` | `object` | 0 |
| `network_status` | `object` | 0 |
| `npi` | `int64` | 0 |
| `contact_number` | `object` | 0 |
| `referral_required` | `object` | 0 |

### referrals.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `referral_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `referring_provider_id` | `object` | 0 |
| `specialist_provider_id` | `object` | 0 |
| `specialty_required` | `object` | 0 |
| `referral_date` | `object` | 0 |
| `expiration_date` | `object` | 0 |
| `referral_status` | `object` | 0 |
| `authorization_status` | `object` | 0 |

### social_history.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `social_history_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `smoking_status` | `object` | 0 |
| `alcohol_history` | `object` | 10 |
| `substance_history` | `object` | 26 |
| `lifestyle_factors` | `object` | 0 |
| `social_risk_factors` | `object` | 9 |
| `clinical_assessment_context` | `object` | 0 |

### surgeries.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `surgery_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `provider_id` | `object` | 0 |
| `surgery_type` | `object` | 0 |
| `surgery_date` | `object` | 0 |
| `surgical_outcome` | `object` | 0 |
| `related_interventions` | `object` | 28 |
| `necessity_evaluation_support` | `object` | 0 |

### vital_signs.csv

| Column Name | Type | Null Count |
| --- | --- | --- |
| `vital_id` | `object` | 0 |
| `patient_id` | `object` | 0 |
| `date_recorded` | `object` | 0 |
| `vital_type` | `object` | 0 |
| `value` | `object` | 0 |
| `unit` | `object` | 0 |
| `abnormal_flag` | `bool` | 0 |
| `severity_indicator` | `object` | 0 |
| `trend` | `object` | 0 |
