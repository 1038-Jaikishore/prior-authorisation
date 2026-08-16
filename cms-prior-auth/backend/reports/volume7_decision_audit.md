# Volume 7: Auditing, Immutability & Safety Log

## 1. Traceability & Versioning

* **Audit Keys**: Every decision result record is linked to unique versioned identifiers:
  * `decision_id`: Unique trial run ID (`DEC-AUTHxxxxx-xxxxxxxx`).
  * `evaluation_id`: The source evaluation run ID used (`EVAL-AUTHxxxxx-xxxxxxxx`).
  * `authorization_id`: The patient prior authorization request ID (`AUTHxxxxx`).
* **Rule Engine Versioning**: Stored under `rule_version = "v1"`.
* **Database Target**: Persisted under collection `decision_support_results`.
* **Immutability Rules**:
  * Prior recommendation trials are never overwritten.
  * Re-running evaluations generates a new `EvaluationBundle`, which outputs a new immutable `DecisionSupportResult` record, preserving historical clinical triage logs for audit purposes.

---

## 2. Leakage Protection Verification

The Decision Support engine consumes the cleaned `EvaluationBundle` and is verified to prevent label leakage.
The following fields are strictly popped/prevented from enters decision rules:
* `ai_reasoning`
* `status` (precomputed request statuses)
* `claim_status`
* `authorization_status`
* `threshold_met`
* `step_therapy_requirement_met`
* `necessity_evaluation_support`

Triage outputs are compiled solely based on active requirements evaluations and coding validator severity checks.
