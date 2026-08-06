<!-- BEGIN MANAGED: AGENT-GOVERNANCE PHASE-2B CLINICAL-AI -->
# Project profile — clinical_ai

- Path: `C:\Avihusitton\clinical_ai`.
- Owner: Avihu Sitton.
- Classification: recently deployed production / production-critical; current live health is unverified.
- Git baseline: branch `main`; HEAD `b3279011ec6e033054a32f7a66cb1bd9a2e24583`; pre-existing dirty state was one untracked `test.js`.
- Phase 2B-B scope: governance adapters and metadata only.

## Authority and chronology

- Shared safety policy is followed by unchanged `.agents\AGENTS.md` (expected SHA-256 `4e5705f28c9b9ca26d137d4953208368754ed3d1d6165ca5330b9d5846fc7146`).
- `PROTECTED_FILES.md`, the safety/restriction fields in `PROJECT_STATE.md`, and `MODEL_ROUTING.md` govern protected implementation and routing.
- `docs\orchestration\UNIFIED_PROGRAM_GOVERNANCE.md` governs the dictionary/clinical boundary; `UNIFIED_PROGRAM_STATE.json` is the later progress record.
- `TASK_TRACKER.md`, current Git evidence, deployment files, and `CHANGELOG.md` establish later actual events.
- `handoff_dictionary_integration\SYSTEM_HANDOFF.md` is a scoped historical/domain handoff dated 2026-07-28, not a canonical whole-project handoff. It recorded preflight not run, unresolved canonical sources, conditional staging writes, forbidden production writes/live clinical traffic/patient data, and deferred runtime alignment.
- `PROJECT_STATE.md` is internally mixed and contains stale portions; `TASK_TRACKER.md` also predates the 2026-08-02 production events.
- `CHANGELOG.md` and Git record a 2026-08-02 Render deployment connected to Neo4j AuraDB, a production Neo4j 403 fix, a Render UI recovery, and later connection diagnostics/credential-whitespace fixes. These events change runtime classification but do not repeal clinical safety prohibitions.

## Cross-project relationship

- `C:\Avihusitton\dherech-dictionery` is the protected canonical knowledge producer.
- Only a signed, manifest-bound D4 package may cross from the dictionary workspace. No direct physical merge or source write is allowed.
- Release evidence: `D4-99F53565A7BCC45E`; Clinical AI owns staging load and rollback responsibilities for an explicitly authorized integration task.
- Governance rollout creates no data transfer and authorizes no write to the dictionary workspace.

## Hard boundaries

No patient or sensitive clinical data; no live clinical traffic; no Render, Neo4j, OpenRouter, or other live-service contact; no production graph write; no credentials; no build, test, deploy, restart, app command, Git mutation, dependency/config change, or protected-file edit. Codex and Antigravity must never write concurrently.
<!-- END MANAGED: AGENT-GOVERNANCE PHASE-2B CLINICAL-AI -->

