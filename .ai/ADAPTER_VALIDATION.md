<!-- BEGIN MANAGED: AGENT-GOVERNANCE PHASE-2B CLINICAL-AI -->
# Adapter validation — clinical_ai

- `validated_at_utc`: `2026-08-04T09:28:33Z`
- `workspace`: `C:\Avihusitton`
- `target_project`: `C:\Avihusitton\clinical_ai`
- `writing_host`: Codex desktop, central session; sole writer.
- `planner_reviewer`: `gpt-5.6-sol`, reasoning `xhigh`, based on active-session evidence previously supplied by the owner.
- `mechanical_validators`: two read-only Codex subagents explicitly dispatched as `gpt-5.6-terra`, reasoning `medium`.
- `validated_targets`: `AGENTS.override.md`; `GEMINI.md`; `.agents\rules\00-shared-governance.md`; `.ai\PROJECT_PROFILE.md`; `.ai\HANDOFF.md`.
- `structure`: passed — exactly one managed block per target and valid Rule frontmatter.
- `required_sources`: passed — referenced required sources exist and declared baseline hashes match.
- `safety`: passed — no obvious secret patterns in new governance files; no unauthorized target; immutable project untouched.
- `git_and_state`: passed — branch/HEAD and pre-existing state preserved; only expected governance files explain new entries where Git applies.
- `cross_project_boundaries`: passed — dependencies are read-only/task-scoped and grant no cross-write.
- `codex_independent_validation`: **PASSED**.
- `codex_fresh_project_automatic_loading`: **PENDING / NOT PROVEN BY THIS CENTRAL VALIDATION**.
- `antigravity_2_0_validation`: **PENDING**.
- `two_host_acceptance`: **PENDING**.
- `persistent_cross_model_router`: **NOT IMPLEMENTED**; the Sol/Terra split above validates controlled delegation in this task only.
- `application_runtime`: not executed or contacted.

This record does not authorize application, Git, dependency, configuration, credential, service, deployment, external-system, or cross-project mutation.
<!-- END MANAGED: AGENT-GOVERNANCE PHASE-2B CLINICAL-AI -->

