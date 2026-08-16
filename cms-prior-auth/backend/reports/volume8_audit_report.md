# Volume 8: Case Auditing & Policy Version Snapshot Report

## 1. Audit Event Logging Timeline
Milestones are tracked using the `AuditEvent` schema in an immutable log collection. Registered event milestones include:
* **`REQUEST_CREATED`**: Patient intake request submitted.
* **`EVIDENCE_PACKET_BUILT`**: Normalized clinical records mapped.
* **`POLICY_ROUTED`**: Active NCD/LCD matches routed.
* **`POLICY_RETRIEVED`**: RAG snippets compiled.
* **`EVALUATION_CREATED`**: Criteria compliance matching finished.
* **`DECISION_SUPPORT_CREATED`**: Decision precedence rules applied.
* **`EXPLANATION_GENERATED`**: Reviewer explanation created.
* **`REVIEWER_ACTION_RECORDED`**: Human action submitted.
* **`RECOMMENDATION_OVERRIDDEN`**: Human override statement persisted.

---

## 2. Policy Version Snapshots
To prevent historical audits from scanning modified policy databases, case logs freeze and store:
* **Jurisdiction active dates**: Effective/revision dates active at execution time.
* **Matched CMS document version**: Preserves NCD IDs, LCD IDs, and Article version counts.
* **Policy chunk IDs**: Frozen RAG context indexes.
