# Volume 8: End-to-End Scenarios Demo Report

## 1. Scenario A: APPROVE Path
* **Request**: CPT code matching active policies with complete patient evidence.
* **Governing Policy**: LCD L33942 & Article A57311
* **Compliance Checks**:
  * Physician Referral: `MET`
  * Joint Diagnosis: `MET`
  * Conservative Treatment: `MET`
  * Coding Validations: `PASS`
* **Disposition Support**: `APPROVE` (Certainty: `HIGH`)
* **Synthesis Explanation**: Structured synthesis confirms full clinical criteria and billing compliance.
* **Reviewer Action**: `ACCEPT_RECOMMENDATION` logs approval event.

---

## 2. Scenario B: DENY Path
* **Request**: Patient request where positive evidence invalidates coverage guidelines.
* **Governing Policy**: NCD 228 (Therapeutic shoes for diabetes)
* **Compliance Checks**:
  * Patient age check: `NOT_MET` (documented age 52, policy requires >= 65)
  * Diagnosis coverage: `FAIL` (noncovered ICD-10 diagnosis explicitly found in noncovered mapping)
* **Disposition Support**: `DENY` (Certainty: `HIGH`)
* **Synthesis Explanation**: Synthesis states blocking failures: diabetes orthosis is not covered for patients under age 65 or with current diagnosis.
* **Reviewer Action**: `ACCEPT_RECOMMENDATION` logs denial event.

---

## 3. Scenario C: PEND Path (Real 97110 Colorado Case)
* **Request**: CPT `97110`, State `CO`, DOS `2026-08-10`, Diagnosis `M17.11`
* **Governing Policy**: LCD `L33942` and companion Article `A57311`
* **Compliance Checks**:
  * Referral: `MET`
  * Conservative treatment: `MET`
  * Joint impairment diagnosis: `UNCLEAR` (Musculoskeletal diagnosis missing from patient condition history)
  * Coding: `WARNING` on `LCD_HCPCS` (bridged via companion Article mapping)
* **Disposition Support**: `PEND` (Certainty: `HIGH`)
* **Synthesis Explanation**: Synthesis identifies missing joint impairment documentation.
* **Reviewer Action**: `REQUEST_MORE_INFORMATION` logs pending action, creating structured information request: *"Provide clinical documentation confirming joint impairment"*

---

## 4. Scenario D: NURSE_REVIEW Path
* **Request**: Patient request with routing ambiguity or conflicting parameters.
* **Governing Policy**: Unresolved conflicting LCDs active in the state.
* **Compliance Checks**:
  * Policy Routing: `POLICY_APPLICABILITY_UNCERTAIN`
* **Disposition Support**: `NURSE_REVIEW` (Certainty: `LOW`)
* **Synthesis Explanation**: Synthesis details policy routing conflict.
* **Reviewer Action**: `ESCALATE` logs escalation to clinical triage staff.

---

## 5. Scenario E: DECISION_SUPPORT_UNAVAILABLE Path
* **Request**: Request with custom procedural codes (e.g. `PROCxxxx`) where no matched CMS reference data exists.
* **Governing Policy**: No routable policy matches.
* **Compliance Checks**:
  * Routing: `POLICY_EVALUATION_UNAVAILABLE`
* **Disposition Support**: `DECISION_SUPPORT_UNAVAILABLE` (Certainty: `LOW`)
* **Synthesis Explanation**: Synthesis explains that no matching CMS rules cover this custom service.
* **Reviewer Action**: `OVERRIDE_RECOMMENDATION` to manually assign disposition.
