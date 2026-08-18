# Patient Field Role Classification Map

This map classifies all columns across the 21 patient datasets to detect and isolate precomputed labels, AI-generated reasonings, or outcome leakage fields.

| Filename | Column | Classification | Reason / Role |
| --- | --- | --- | --- |
| `allergies.csv` | `allergy_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `allergies.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `allergies.csv` | `allergen_type` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `allergies.csv` | `allergen_name` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `allergies.csv` | `reaction_severity` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `allergies.csv` | `onset_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `allergies.csv` | `active_status` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `allergies.csv` | `conflict_alert_flag` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `authorization_requests.csv` | `request_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `authorization_requests.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `authorization_requests.csv` | `provider_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `authorization_requests.csv` | `requested_procedure_code` | **RAW_CLINICAL_FACT** | Raw structured clinical code (e.g. HCPCS, CPT, ICD-10). |
| `authorization_requests.csv` | `diagnosis_code` | **RAW_CLINICAL_FACT** | Raw structured clinical code (e.g. HCPCS, CPT, ICD-10). |
| `authorization_requests.csv` | `clinical_indication` | **SOURCE_TEXT** | Clinical narrative text block containing patient facts. |
| `authorization_requests.csv` | `medical_necessity` | **SOURCE_TEXT** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `authorization_requests.csv` | `provider_justification` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `authorization_requests.csv` | `urgency` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `authorization_requests.csv` | `requested_quantity` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `authorization_requests.csv` | `requested_duration_days` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `authorization_requests.csv` | `request_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `authorization_requests.csv` | `status` | **OUTCOME_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `authorization_requests.csv` | `previous_treatment_info` | **SOURCE_TEXT** | Clinical narrative text block containing patient facts. |
| `authorization_requests.csv` | `supporting_evidence_url` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `authorization_requests.csv` | `ai_reasoning` | **AI_GENERATED_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `care_plans.csv` | `plan_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `care_plans.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `care_plans.csv` | `provider_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `care_plans.csv` | `current_treatment_plan` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `care_plans.csv` | `planned_procedures` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `care_plans.csv` | `treatment_goals` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `care_plans.csv` | `start_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `care_plans.csv` | `end_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `care_plans.csv` | `treatments_attempted` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `care_plans.csv` | `status` | **OUTCOME_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `claims.csv` | `claim_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `claims.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `claims.csv` | `provider_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `claims.csv` | `procedure_code` | **RAW_CLINICAL_FACT** | Raw structured clinical code (e.g. HCPCS, CPT, ICD-10). |
| `claims.csv` | `diagnosis_code` | **RAW_CLINICAL_FACT** | Raw structured clinical code (e.g. HCPCS, CPT, ICD-10). |
| `claims.csv` | `claim_status` | **OUTCOME_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `claims.csv` | `treatment_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `claims.csv` | `service_type` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `claims.csv` | `treatment_name` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `claims.csv` | `amount_billed` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `claims.csv` | `amount_paid` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `claims.csv` | `treatment_frequency` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `claims.csv` | `step_therapy_verified` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `claims.csv` | `previous_auth_history` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `claims.csv` | `duplicate_service_flag` | **PRECOMPUTED_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `clinical_assessments.csv` | `assessment_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `clinical_assessments.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `clinical_assessments.csv` | `assessment_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `clinical_assessments.csv` | `assessment_type` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `clinical_assessments.csv` | `score` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `clinical_assessments.csv` | `severity_level` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `clinical_assessments.csv` | `threshold_met` | **PRECOMPUTED_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `clinical_assessments.csv` | `progression_trend` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `conditions.csv` | `condition_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `conditions.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `conditions.csv` | `diagnosis_code` | **RAW_CLINICAL_FACT** | Raw structured clinical code (e.g. HCPCS, CPT, ICD-10). |
| `conditions.csv` | `diagnosis_name` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `conditions.csv` | `onset_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `conditions.csv` | `resolution_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `conditions.csv` | `condition_type` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `conditions.csv` | `relevant_to_procedure_flag` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `coverage.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `coverage.csv` | `plan_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `coverage.csv` | `insurance_company` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `coverage.csv` | `plan_type` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `coverage.csv` | `effective_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `coverage.csv` | `expiry_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `coverage.csv` | `is_active` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `coverage.csv` | `requires_prior_auth` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `coverage.csv` | `benefits_summary` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `coverage.csv` | `covered_services` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `coverage.csv` | `copay_amount` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `coverage.csv` | `deductible` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `diagnostic_results.csv` | `result_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `diagnostic_results.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `diagnostic_results.csv` | `test_name` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `diagnostic_results.csv` | `test_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `diagnostic_results.csv` | `result_value` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `diagnostic_results.csv` | `reference_range` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `diagnostic_results.csv` | `abnormal_flag` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `diagnostic_results.csv` | `evidence_for_medical_necessity` | **SOURCE_TEXT** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `encounters.csv` | `encounter_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `encounters.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `encounters.csv` | `provider_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `encounters.csv` | `encounter_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `encounters.csv` | `encounter_type` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `encounters.csv` | `primary_diagnosis_code` | **RAW_CLINICAL_FACT** | Raw structured clinical code (e.g. HCPCS, CPT, ICD-10). |
| `encounters.csv` | `discharge_status` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `encounters.csv` | `follow_up_required` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `encounters.csv` | `recent_hospitalization_flag` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `family_history.csv` | `history_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `family_history.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `family_history.csv` | `family_member_relation` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `family_history.csv` | `condition` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `family_history.csv` | `age_of_onset` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `family_history.csv` | `genetic_risk_indicator` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `functional_status.csv` | `status_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `functional_status.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `functional_status.csv` | `assessment_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `functional_status.csv` | `physical_functional_status` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `functional_status.csv` | `mental_functional_status` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `functional_status.csv` | `quality_of_life_score` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `functional_status.csv` | `deterioration_detected` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `functional_status.csv` | `pre_post_treatment_flag` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `functional_status.csv` | `rehab_support_needed` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `immunizations.csv` | `immunization_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `immunizations.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `immunizations.csv` | `vaccine_name` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `immunizations.csv` | `dose_number` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `immunizations.csv` | `date_administered` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `immunizations.csv` | `next_due_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `immunizations.csv` | `status` | **OUTCOME_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `medical_equipment.csv` | `equipment_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `medical_equipment.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `medical_equipment.csv` | `equipment_type` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `medical_equipment.csv` | `date_issued` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `medical_equipment.csv` | `expected_replacement_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `medical_equipment.csv` | `current_status` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `medical_equipment.csv` | `usage_frequency` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `medical_equipment.csv` | `duplicate_request_flag` | **PRECOMPUTED_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `medications.csv` | `medication_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `medications.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `medications.csv` | `medication_name` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `medications.csv` | `dosage` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `medications.csv` | `start_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `medications.csv` | `end_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `medications.csv` | `status` | **OUTCOME_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `medications.csv` | `step_therapy_requirement_met` | **PRECOMPUTED_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `patients.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `patients.csv` | `first_name` | **ADMINISTRATIVE_FACT** | Administrative or demographic patient metadata. |
| `patients.csv` | `last_name` | **ADMINISTRATIVE_FACT** | Administrative or demographic patient metadata. |
| `patients.csv` | `dob` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `patients.csv` | `age` | **ADMINISTRATIVE_FACT** | Administrative or demographic patient metadata. |
| `patients.csv` | `gender` | **ADMINISTRATIVE_FACT** | Administrative or demographic patient metadata. |
| `patients.csv` | `insurance_plan` | **ADMINISTRATIVE_FACT** | Administrative or demographic patient metadata. |
| `patients.csv` | `member_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `patients.csv` | `summary_card_text` | **SOURCE_TEXT** | Clinical narrative text block containing patient facts. |
| `procedures.csv` | `procedure_record_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `procedures.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `procedures.csv` | `provider_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `procedures.csv` | `procedure_code` | **RAW_CLINICAL_FACT** | Raw structured clinical code (e.g. HCPCS, CPT, ICD-10). |
| `procedures.csv` | `procedure_name` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `procedures.csv` | `procedure_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `procedures.csv` | `outcome` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `procedures.csv` | `related_to_current_request` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `providers.csv` | `provider_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `providers.csv` | `first_name` | **ADMINISTRATIVE_FACT** | Administrative or demographic patient metadata. |
| `providers.csv` | `last_name` | **ADMINISTRATIVE_FACT** | Administrative or demographic patient metadata. |
| `providers.csv` | `specialty` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `providers.csv` | `facility_name` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `providers.csv` | `network_status` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `providers.csv` | `npi` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `providers.csv` | `contact_number` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `providers.csv` | `referral_required` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `referrals.csv` | `referral_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `referrals.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `referrals.csv` | `referring_provider_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `referrals.csv` | `specialist_provider_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `referrals.csv` | `specialty_required` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `referrals.csv` | `referral_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `referrals.csv` | `expiration_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `referrals.csv` | `referral_status` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `referrals.csv` | `authorization_status` | **OUTCOME_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `social_history.csv` | `social_history_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `social_history.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `social_history.csv` | `smoking_status` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `social_history.csv` | `alcohol_history` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `social_history.csv` | `substance_history` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `social_history.csv` | `lifestyle_factors` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `social_history.csv` | `social_risk_factors` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `social_history.csv` | `clinical_assessment_context` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `surgeries.csv` | `surgery_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `surgeries.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `surgeries.csv` | `provider_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `surgeries.csv` | `surgery_type` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `surgeries.csv` | `surgery_date` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `surgeries.csv` | `surgical_outcome` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `surgeries.csv` | `related_interventions` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `surgeries.csv` | `necessity_evaluation_support` | **PRECOMPUTED_LABEL** | Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth. |
| `vital_signs.csv` | `vital_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `vital_signs.csv` | `patient_id` | **ADMINISTRATIVE_FACT** | Primary/Foreign database tracking identifier. |
| `vital_signs.csv` | `date_recorded` | **ADMINISTRATIVE_FACT** | Chronological timestamp record. |
| `vital_signs.csv` | `vital_type` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `vital_signs.csv` | `value` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `vital_signs.csv` | `unit` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `vital_signs.csv` | `abnormal_flag` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `vital_signs.csv` | `severity_indicator` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |
| `vital_signs.csv` | `trend` | **RAW_CLINICAL_FACT** | Structured raw clinical measure or metric value. |