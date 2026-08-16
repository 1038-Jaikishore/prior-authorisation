# Volume 8: Explanation Validation Report

## 1. Validation Logic & Safety Guardrails
To prevent the LLM from altering decisions, inventing facts, or hallucinating policy/clinical references, the `DecisionExplanationService` applies the following programmatic validations before accepting and displaying any generated synthesis:

* **Disposition Consistency**: The LLM completion JSON MUST contain a recommended disposition matching exactly the structured engine's triage choice (e.g. `PEND`). If there is a mismatch (such as trying to change `PEND` to `APPROVE`), the explanation is rejected.
* **Grounding Limits**: Synthesized text is grounded only in the provided context (Decision Factors, matched clinical items, and active CMS citations).
* **Reference Boundary Enforcement**: References to NCDs, LCDs, Articles, or patient IDs must match the pre-approved IDs present in the `EvaluationBundle`.

---

## 2. Deterministic Fallback Behavior
The system maintains absolute independence from the LLM synthesis layer. In case of any of the following failures:
1. **API Timeout / Connection Errors**: OpenRouter/LLM endpoint timeouts or returns 5xx errors.
2. **Schema Incompatibility**: LLM fails to return valid, parseable JSON matching the Pydantic template.
3. **Validation Failure**: Mismatched dispositions or unsupported references.

The service immediately triggers an audit event log `EXPLANATION_VALIDATION_FAILED` and falls back to generating a deterministic, rule-based clinical explanation which is fully traceable.
