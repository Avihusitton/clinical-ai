---
name: clinical-ai-governor
description: Governance and policy enforcement skill for Clinical AI. Distinguishes agent models from runtime LLM providers, validates content/engineering readiness, and enforces security and protected file rules.
---

# Clinical AI Governor Skill

## Overview
The Clinical AI Governor provides non-blocking policy validation, state tracking, and action classification across the codebase.

## Action Classification Matrix
1. `SAFE_LOCAL`: Safe local operations (reading files, AST inspection, local pytest, hash recomputation).
2. `REQUIRES_VERIFICATION`: Architecture changes, design freeze updates, schema modifications.
3. `REQUIRES_OWNER_APPROVAL`: Git commits, package installations, production code modifications, file deletions/moves.
4. `BLOCKED_BY_SECURITY`: PII leaks, credential printing, live patient data usage, unauthorized network access.

## Core Rules
- **Agent vs Runtime Separation**: Development agents (Google Antigravity environment) prefer Gemini 3.6 Flash. Runtime LLM calls require OpenRouter targeting DeepSeek v4 Pro.
- **Content Readiness**: The project owner granted human editorial approval for the concept dictionary and Official Glossary on 2026-07-28. Technical preflight is `NOT_RUN`, and canonical source identity is `UNRESOLVED`.
- **Neo4j Authorization**: Staging writes are `CONDITIONALLY_AUTHORIZED` only after canonical-source identification, complete preflight, identifier screening, dry run, verified non-production target identity, batch-scoped rollback, and zero blocking errors. Production writes are forbidden.
- **Clinical Data Safety**: Live patient data and live clinical traffic are forbidden.
- **Credential Risk Exception**: On 2026-07-28, the project owner temporarily accepted the risk of the two still-exposed OpenRouter literals, reporting a total spend limit of USD 45, so dictionary and Neo4j staging work may continue. This does not prove rotation or local containment and does not authorize printing, copying, testing, or using either credential. Owner follow-up to rotate and move the value to an approved secret store remains required.
- **Runtime Alignment**: Runtime-model alignment is deferred and must not be combined with dictionary governance or staging-ingestion work.
- **Engineering Readiness**: Gates A–D CLOSED, Controlled Integration IMPLEMENTED_AND_AUDITED, Wave 7 PASS_WITH_REQUIRED_PREIMPLEMENTATION_CORRECTIONS.
- **Archive Exclusion**: Files under `_archive/**` are excluded from normal agent task packets and retained for historical recovery only.
- **Protected Files**: `retrieval.py`, `ingestion_pipeline.py`, `build_glossary.py`, `run_full_pipeline.py`, `master_dashboard.py`, `review_app.py`, `config.py`, `llm_client.py`, `gate_c/**`, `gate_d/**`, `gate_cd_boundary/**`, `controlled_integration/**`.

## Current Governance State

```text
EDITORIAL_STATUS: APPROVED
TECHNICAL_PREFLIGHT_STATUS: NOT_RUN
CANONICAL_SOURCE_STATUS: UNRESOLVED
NEO4J_STAGING_WRITE_STATUS: CONDITIONALLY_AUTHORIZED
NEO4J_PRODUCTION_WRITE_STATUS: FORBIDDEN
LIVE_CLINICAL_TRAFFIC_STATUS: FORBIDDEN
PATIENT_DATA_STATUS: FORBIDDEN
RUNTIME_ALIGNMENT_STATUS: DEFERRED
```
