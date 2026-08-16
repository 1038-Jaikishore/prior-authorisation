# Volume 7: Decision Fixture Results Report

## 1. Golden Fixture Paths & Outcomes

### Case A — Approval Path
* **Summary**: All clinical requirements `MET`. Coding validation checks returned `PASS` or `NOT_EVALUATED`.
* **Recommended Disposition**: `APPROVE`
* **Certainty**: `HIGH`
* **Reason Codes**: `PA_ALL_MANDATORY_CRITERIA_MET`
* **Audited Factors**: `FAC-REQ-01` (Referral ➔ MET ➔ Supports Approval)

### Case B — Denial Path
* **Summary**: Mandatory clinical requirements mapped as `NOT_MET` (e.g. age/duration check failure).
* **Recommended Disposition**: `DENY`
* **Certainty**: `HIGH`
* **Reason Codes**: `PA_MANDATORY_CRITERION_NOT_MET`
* **Audited Factors**: `FAC-REQ-01` (Age limit ➔ NOT_MET ➔ Blocking Failure)

### Case C — Pend Path
* **Summary**: Clinical requirements return `UNCLEAR` due to missing documentation in patient history.
* **Recommended Disposition**: `PEND`
* **Certainty**: `HIGH`
* **Reason Codes**: `PA_MANDATORY_CRITERION_UNCLEAR`
* **Missing Information Requests**: Generated `CLINICAL_DOCUMENTATION` request for physician referral.

### Case D — Nurse Review Path
* **Summary**: Geography state code missing or multiple conflicting active LCDs match.
* **Recommended Disposition**: `NURSE_REVIEW`
* **Certainty**: `LOW`
* **Reason Codes**: `PA_POLICY_UNCERTAIN`
* **Audited Factors**: Escalated for manual clinical/geographical triage.

---

## 2. Real Physical Therapy `97110` Colorado Fixture
* **HCPCS**: `97110` | **State**: `CO` | **Date**: `2026-08-10` | **Diagnosis**: `M17.11`
* **Resolution**:
  * Final Applicable LCD: `L33942`
  * Related reference Article: `A57311`
  * Related NCD: `22` (Role: `RELATED_REFERENCE`)
* **Clinical requirements**:
  * Referral requirement: `MET` (Supports Approval)
  * Joint impairment diagnosis requirement: `UNCLEAR` (Musculoskeletal diagnosis missing from patient history records)
  * Conservative treatment duration requirement: `MET` (Supports Approval)
* **Recomputed Decision**:
  * **Recommended Disposition**: `PEND`
  * **Reason Code**: `PA_MANDATORY_CRITERION_UNCLEAR`
  * **Certainty**: `HIGH`
  * **Missing Information**: `CLINICAL_DOCUMENTATION` request generated: *"Provide documentation confirming compliance with requirement: The patient must have a documented diagnosis of joint or musculoskeletal impairment"*
