# Volume 7: Decision Engine Rules and Precedence Matrix

## 1. Decision Precedence Levels

The decision support engine applies the following deterministic triage precedence order:

1. **Policy/Routing Uncertainty** (`POLICY_EVALUATION_UNAVAILABLE` or `POLICY_APPLICABILITY_UNCERTAIN`)
   * *Outcome*: `DECISION_SUPPORT_UNAVAILABLE` or `NURSE_REVIEW` (Certainty: `LOW`)
2. **Hard Deterministic Exclusion** (Explicitly failed coding validations or MAC geography/effective dates failures)
   * *Outcome*: `DENY` (Certainty: `HIGH`)
3. **Mandatory Clinical NOT_MET** (Clinical requirement evaluated as `NOT_MET`)
   * *Outcome*: `DENY` (Certainty: `HIGH`)
4. **Mandatory Clinical UNCLEAR / Blocking Clinical Missing Information** (Unclear/insufficient mandatory clinical records)
   * *Outcome*: `PEND` (Certainty: `HIGH`)
5. **Nurse Review Flags / Manual Review Conditions** (Ambiguous requirements, manual coding checks)
   * *Outcome*: `NURSE_REVIEW` (Certainty: `LOW`)
6. **All Mandatory Requirements Satisfied** (MET or NOT_APPLICABLE clinical criteria)
   * *Outcome*: `APPROVE` (Certainty: `HIGH` if zero warnings, `MODERATE` if warnings exist)

---

## 2. Validator Severity Mapping

| Validator | Status | Severity | Effect on Recommendation |
| :--- | :--- | :--- | :--- |
| **ARTICLE_ICD10** | `FAIL` | `BLOCKING_FAIL` | `DENY` |
| **ARTICLE_ICD10** | `PASS` | `PASS` | `SUPPORTS_APPROVAL` |
| **ARTICLE_ICD10** | `UNKNOWN` | `NON_BLOCKING_WARNING` | Does not block `APPROVE` |
| **ARTICLE_HCPCS** | `FAIL` | `BLOCKING_FAIL` | `DENY` |
| **ARTICLE_HCPCS** | `PASS` | `PASS` | `SUPPORTS_APPROVAL` |
| **LCD_HCPCS** | `FAIL` | `BLOCKING_FAIL` | `DENY` |
| **LCD_HCPCS** | `WARNING` | `NON_BLOCKING_WARNING` | Does not block `APPROVE` |
| **ARTICLE_MODIFIER** | `FAIL` | `BLOCKING_FAIL` | `DENY` |
| **ARTICLE_MODIFIER** | `UNKNOWN` | `NON_BLOCKING_WARNING` | Does not block `APPROVE` |
| **ARTICLE_BILL_TYPE** | `NOT_EVALUATED` | `INFORMATIONAL` | Does not block `APPROVE` |
| **ARTICLE_REVENUE_CODE** | `NOT_EVALUATED` | `INFORMATIONAL` | Does not block `APPROVE` |
| **JURISDICTION** | `FAIL` | `BLOCKING_FAIL` | `DENY` |
| **DATE_AND_VERSION** | `FAIL` | `BLOCKING_FAIL` | `DENY` |

---

## 3. Reason Code Dictionary

* **`PA_POLICY_UNAVAILABLE`**: Custom procedural requests (e.g. `PROCxxxx`) where no matching CMS policies are indexed.
* **`PA_POLICY_UNCERTAIN`**: Ambiguity in state location or multiple geographically active LCD matches.
* **`PA_CODING_BLOCKING_FAILURE`**: Deterministic exclusions like non-covered diagnosis mappings or date boundaries.
* **`PA_MANDATORY_CRITERION_NOT_MET`**: Explicit clinical criterion failed to match.
* **`PA_MANDATORY_CRITERION_UNCLEAR`**: Missing clinical facts or required diagnostic tests.
* **`PA_MANUAL_REVIEW_REQUIRED`**: Manual coding checks or complex conditional clauses.
* **`PA_NONBLOCKING_CODING_WARNING`**: Mapped via related Articles rather than direct LCD lists, or missing optional billing records.
* **`PA_ALL_MANDATORY_CRITERIA_MET`**: All clinical requirements satisfied.
