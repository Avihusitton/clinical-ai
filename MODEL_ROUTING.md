# Model Routing Policy

## 1. Developer Subagent Routing (Antigravity Environment)
- **Primary Orchestrator**: Gemini 3.6 Flash — HIGH
- **Architecture & Audit Agents**: Gemini 3.6 Flash — HIGH
- **Test-Plan & Documentation Agents**: Gemini 3.6 Flash — MEDIUM
- **Hash, AST & Schema Validators**: Gemini 3.6 Flash — LOW

*Rationale*: High quota availability in Google Antigravity environment.

## 2. Production Application Runtime Routing (Clinical AI Runtime)
- **Runtime LLM Provider**: OpenRouter
- **Quality Mode**: DeepSeek v4 Pro
- **Fast / Economy Mode**: DeepSeek v4 Flash
- **Fallback / Legacy Default**: Configuration-driven via `config.py` and `llm_client.py`
- **Grounding Contract**: Send only the current question, a compact rolling
  conversation summary, the eight most recent messages, and a bounded canonical
  D4 graph context. Retrieval may select up to ten approved cards plus approved
  relations and `METHOD_PRIMARY` source locators. Short follow-ups also use up
  to three recent user-authored updates, never assistant text. Never query or
  send quarantine content or the full dictionary.
- **Quality Contract**: Quality mode performs two calls over the same bounded
  evidence: a fact/missing-information/lens analysis with a grounded draft,
  followed by an independent correction pass. Reviewer scores and critique stay
  internal; only the corrected answer is shown.
- **Visible Answer Contract**: Do not show internal card IDs. When decisive
  information is missing, return up to three clarification questions before a
  treatment strategy. Explicitly separate supplied facts from hypotheses and
  prefer a concrete event over a general diagnosis.
- **Accounting Contract**: Use OpenRouter's returned usage cost, retain USD only
  as audit metadata, sum both stages, and show the user an ILS estimate with the
  dated exchange rate plus total generation duration.
- **Availability Contract**: When Pro fails for a model or connection reason,
  retry the stage on Flash. Authentication, credit, and data-policy failures
  remain fail-closed.

*Policy*: Do NOT create a Gemini-only runtime policy. OpenRouter and DeepSeek remain permitted and required for production LLM calls.

The current loopback application is a local, non-production environment.
Profile selection is workspace separation only; an authenticated allowlist for
the two approved identities is required before Internet deployment or live
clinical use.
