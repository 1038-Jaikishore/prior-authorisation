# Volume 8: Reviewer Workflow & Action Log Report

## 1. Human Reviewer Workflow Steps

The reviewer portal maps a structured visual lifecycle for auditing cases:
1. **Case Queue**: Reviewer filters and selects active prior authorization requests.
2. **Patient & Service**: Inspects patient history, prior treatments, requested code, state MAC region, and clinical indicators.
3. **CMS Policy Routing**: Verifies active LCD/Article regulations matching geography and diagnosis.
4. **Requirements Matrix**: Reviews matches (`MET`, `NOT_MET`, `UNCLEAR`) and traces to source database records.
5. **Coding & Administrative Validation**: Verifies jurisdiction and date boundaries.
6. **Decision Support & Explanation**: Inspects system-generated recommendation summary.
7. **Action Timeline & Submissions**: Reviews event milestones and submits workflow outcomes.

---

## 2. Reviewer Actions & Override Preservation

Reviewers can log manual triage outcomes using the action model:
* **`ACCEPT_RECOMMENDATION`**: Accepts system recommendation.
* **`REQUEST_MORE_INFORMATION`**: Requests qualifying patient records.
* **`ESCALATE`**: Escalates to senior directors.
* **`OVERRIDE_RECOMMENDATION`**: Overrides system recommendation (requires explicit intended status and reason statement).

> [!IMPORTANT]
> The system enforces strict separation of recommendations and reviewer actions. Overriding a recommendation writes a new history action entry while leaving the original `DecisionSupportResult` intact in the database for compliance auditing.
