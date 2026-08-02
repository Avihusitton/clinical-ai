# Project State & Governance Baseline

```yaml
gates_status:
  gate_a: CLOSED
  gate_b: CLOSED
  gate_c: CLOSED
  gate_d: CLOSED

governance_status:
  EDITORIAL_STATUS: APPROVED
  TECHNICAL_PREFLIGHT_STATUS: PASS_CANONICAL
  CANONICAL_SOURCE_STATUS: D4-99F53565A7BCC45E
  NEO4J_STAGING_WRITE_STATUS: CONDITIONALLY_AUTHORIZED
  NEO4J_PRODUCTION_WRITE_STATUS: FORBIDDEN
  LIVE_CLINICAL_TRAFFIC_STATUS: FORBIDDEN
  PATIENT_DATA_STATUS: FORBIDDEN
  RUNTIME_ALIGNMENT_STATUS: DEFERRED

engineering_readiness:
  controlled_integration: IMPLEMENTED_AND_AUDITED
  wave_7_status: PASS_WITH_REQUIRED_PREIMPLEMENTATION_CORRECTIONS
  production_shadow_wiring: NOT_IMPLEMENTED
  local_method_qa: PASS_D4_CANONICAL_LOCAL_READ_ONLY
  local_method_qa_ui: RUNNING_ON_LOOPBACK
  local_method_qa_e2e: PASS
  local_method_qa_ai_option: PASS_ENABLED_DEDICATED_SECRET
  local_method_qa_ai_grounding: D4_RICH_BALANCED_CONTEXT_FAIL_SAFE
  local_method_qa_ai_quality_review: PASS_TWO_STAGE_INTERNAL
  local_method_qa_ai_live_e2e: PASS_DEEPSEEK_V4_PRO_TWO_STAGE
  internal_clinical_pilot: NOT_READY

program_management:
  mode: UNIFIED_DUAL_WORKSPACE
  physical_merge_status: NOT_PERFORMED_BY_DESIGN
  dictionary_workspace: C:\Avihusitton\dherech-dictionery\Derech_Dictionary_Project
  dictionary_asset_class: SPECIAL_PROTECTED_CONTENT_ZONE
  dictionary_gate_5_status: COMPLETE
  dictionary_semantic_review_items: 0
  dictionary_primary_cards_reparsed: 174
  dictionary_primary_cards_critical_complete: 174
  dictionary_primary_name_mismatch_under_review: NONE
  dictionary_preview_status: PASS_PREVIEW_ACCEPTED_FOR_WRITE_FREE_ADAPTER
  dictionary_preview_graph_plan: GRAPHPLAN-55C4A53B9B06B1F8
  dictionary_preview_staging_dry_run: PASS_ZERO_ERRORS_ZERO_WRITES
  chunk_context_migration_audit: PASS_WRITE_FREE
  pending_chunk_context_candidates: 32
  chunk_context_automatic_promotions: 0
  durable_chunk_package_contract: IMPLEMENTED_AND_TESTED
  chunk_card_id_load_planner: IMPLEMENTED_AND_TESTED
  neo4j_target_static_audit: PASS_EXPLICIT_NONPRODUCTION
  neo4j_runtime_target_verification: PASS_NONPRODUCTION
  dictionary_staging_load: PASS
  dictionary_ingestion_batch_id: DICTBATCH-E9C8ECB4A7372979BA57
  context_quarantine_staging_load: PASS
  context_ingestion_batch_id: CONTEXTBATCH-39118BDE64AEDA51FB43
  neo4j_desktop_tracking_status: RECONCILED_TO_LIVE_LAUNCHER
  local_method_qa_url: http://127.0.0.1:8765
  canonical_staging_loader: IMPLEMENTED_AND_TESTED_FAIL_CLOSED
  exact_batch_rollback: IMPLEMENTED
  canonical_chunk_staging_loader: IMPLEMENTED_DICTIONARY_FIRST
  unified_control_document: docs/orchestration/UNIFIED_PROGRAM_GOVERNANCE.md
  owner_attention_required_now: false

runtime_configuration:
  developer_agent_model: Gemini 3.6 Flash
  runtime_provider: OpenRouter
  intended_runtime_model: DeepSeek v4 Pro
  local_method_qa_provider: DETERMINISTIC_DEFAULT_OPTIONAL_OPENROUTER
  local_method_qa_ai_models: deepseek/deepseek-v4-pro_default_and_deepseek/deepseek-v4-flash
  local_method_qa_network_scope: LOOPBACK_DEFAULT_OPT_IN_EXTERNAL_AI

security_restrictions:
  live_patient_data_allowed: false
  live_clinical_traffic_allowed: false
  neo4j_production_mutation_allowed: false
  external_network_allowed: false
  openrouter_exposure_risk_accepted_temporarily: true
  openrouter_credential_use_allowed: false
  credential_rotation_verified: false
```

## Description of Baseline Facts

1. **Content Readiness**: On 2026-07-28, the project owner confirmed human editorial approval of the concept dictionary and Official Glossary. This approval is editorial only: technical preflight has not run and canonical source paths remain unresolved.
2. **Neo4j Authorization**: A future write to Neo4j staging is conditionally authorized only after canonical-source identification, complete technical preflight, identifier screening, dry run, explicit non-production target verification, rollback by `ingestion_batch_id`, and zero blocking errors. Neo4j production writes remain forbidden.
3. **Clinical Safety**: Live patient data and live clinical traffic remain forbidden.
4. **Development Agents**: Antigravity development agents use Gemini models (`Gemini 3.6 Flash`) due to high Google environment quota availability.
5. **Runtime Model**: The intended runtime LLM provider is OpenRouter targeting DeepSeek v4 Pro. Gemini models are NOT forced as runtime models. Runtime alignment is deferred and is not part of the governance-reconciliation task.
- **Credential Risk Exception**: On 2026-07-28, the owner accepted the temporary risk of the two exposed OpenRouter literals, reporting a total spend limit of USD 45, so the dictionary and Neo4j staging path may continue. The literals must not be printed or used; rotation and local secret-store migration remain pending.
6. **Engineering Baseline**: Gates A–D are closed and audited. Controlled Integration package is implemented and audited. Production shadow wiring into `retrieval.py` is NOT implemented. Internal clinical pilot is NOT ready.
7. **Unified Program Management**: On 2026-07-29, Clinical AI and Derech Dictionary were placed under one management program while remaining separate physical workspaces. Dictionary source files and editorial artifacts retain special protected status; only manifest-bound preview or canonical release packages cross the boundary.
8. **Preview Staging Proof**: The Preview graph plan passed an independent write-free staging dry run with 20 planned nodes, 33 planned relationships, zero rejected records, zero identifier-screening findings, and zero Neo4j connections or writes. It remains ineligible for execution because it is not a canonical release and no staging target has been verified.
9. **Chunk Context Migration**: The legacy inventory contains 13 baseline chunk relationships and 32 pending contextual relationship candidates across 20 chunk IDs. All candidates remain quarantined; zero were automatically promoted. Final migration must remap legacy names to canonical `card_id` values after the full dictionary release and must use a durable chunk export.
10. **Durable Chunk Contract**: A separate acceptance gate now validates manifest hashes, unique chunk IDs, de-identification status, patient-data prohibition, direct-identifier screening, relationship review state, and canonical dictionary release identity. A write-free planner emits `Chunk -> GlossaryEntry` edges only when every `card_id` exists in the accepted dictionary graph plan.
11. **Dictionary Gate 5 Live Progress**: All 746 relation-text rows were triaged without approval promotion; 694 remain explicit relation candidates and 301 unanchored rows remain preserved. All 174 partial primary cards were reparsed to critical completeness from source material. The latest producer report has one isolated name-match failure (`H501`) under review; all other reparse checks passed.
12. **Neo4j Target Static Audit**: The configured target has explicit non-production markers and configured credentials. The audit emitted no secrets and made zero connections. Runtime read-only verification remains intentionally deferred until the canonical dictionary release passes local preflight.
13. **Canonical Staging Loader**: A new fail-closed loader consumes only manifest-verified graph plans keyed by `card_id`, blocks Preview and Production, requires canonical unified preflight plus explicit non-production classification, writes a preload snapshot before mutation, performs post-load count validation, and supports exact-batch data rollback. It does not use the rejected Legacy default paths.
14. **Canonical Chunk Staging Loader**: A separate dictionary-first loader requires a durable accepted chunk package, matching dictionary load evidence, passed dictionary post-load validation, and runtime existence of every `GlossaryEntry` endpoint. Pending context-queue rows remain excluded and automatic promotions remain zero.
15. **Identifier Screening Precision**: Structured source IDs and SHA-256 tokens are removed from the human-text screening surface before nine-digit identifier checks. A dedicated regression test proves that structured provenance is not falsely blocked while a genuine nine-digit candidate remains blocked.
16. **Canonical Dictionary Release**: Gate 5 completed with signed release `D4-99F53565A7BCC45E`. All 22 producer checks passed. The release contains 946 documented records, 874 active identifiers, 72 redirects, 6,721 approved cross-references, 1,210 source-map rows, 873 quarantined relation candidates, and zero blocked cards.
17. **Canonical Clinical Preflight**: Independent acceptance, graph planning, identifier screening, and write-free staging dry run passed with zero errors and zero rejected records. Plan `GRAPHPLAN-37D441363E44ED86` contains 1,023 nodes and 8,003 approved relationships; all 873 dictionary candidates remain outside the load plan.
18. **Neo4j Runtime Gate**: Static non-production classification and all local execution gates pass. Runtime read-only verification could not connect because no Neo4j service is listening on the configured local endpoint. No database reads or writes occurred.
19. **Chunk Reconstruction Evidence**: A no-LLM, no-API scan of 343 local source documents matched 11 of 20 legacy chunk identifiers. Nine identifiers were not reconstructable and five matched identifiers did not reproduce the stored de-identified excerpt. No raw chunk package was emitted because the fail-closed reconstruction gate did not pass.
20. **Context Quarantine Package**: All 32 relation candidates and 20 stored de-identified evidence excerpts were preserved in `CONTEXTQUARANTINE-786B27A48BD861F2`. Nine candidates have two unique dictionary endpoints and 23 remain partially mapped. Plan `CONTEXTPLAN-DF2A0F311DCC4BAE` creates only quarantine/evidence structures, zero canonical semantic relations, and zero automatic promotions.
21. **Dictionary Staging Load**: The local non-production Neo4j target passed read-only verification. Batch `DICTBATCH-E9C8ECB4A7372979BA57` loaded or updated 1,023 dictionary nodes and 8,003 approved relationships. Post-load validation matched both expected counts exactly; a preload snapshot and rollback evidence path were retained.
22. **Context Quarantine Staging Load**: After the dictionary load, batch `CONTEXTBATCH-39118BDE64AEDA51FB43` loaded 52 evidence/candidate nodes and 73 quarantine-only relationships. Post-load validation matched expected counts exactly. Zero canonical semantic edges and zero automatic promotions were loaded.
23. **Post-load Runtime State**: The `neo4j` database contains 1,125 total nodes and 8,093 total relationships, including the pre-existing graph, the canonical dictionary, and the quarantined context layer. Production execution remains forbidden.
24. **Local Method Q&A Runtime**: A loopback-only, read-only Q&A service is running at `http://127.0.0.1:8765`. Its deterministic path queries only approved D4 glossary entries and approved D4 relationships. The optional AI path additionally consumes approved `METHOD_PRIMARY` evidence locators. Quarantine is neither queried nor displayed by the active runtime. The service requires an explicit no-patient-data confirmation, blocks direct identifiers, and retains the deterministic fallback. End-to-end acceptance resolved A002 and A008 correctly, and graph counts remained exactly 1,125 nodes and 8,093 relationships before and after both questions. This readiness applies to local method-knowledge and synthetic scenarios only; live clinical traffic and the internal clinical pilot remain forbidden.
25. **Optional AI Synthesis**: An opt-in, graph-grounded OpenRouter synthesis path is implemented behind a UI checkbox and is enabled from the dedicated ignored secret file. The legacy root `.env` key is ignored; independent credential-rotation verification remains pending. Balanced retrieval can select up to ten approved D4 cards, 36 approved relations, and approved primary-source locators inside a 32,000-character cap. Follow-up retrieval incorporates only recent user-authored updates, and a post-clarification direction request is required to receive a provisional answer instead of another clarification loop. Quality mode performs a grounded analysis/draft followed by an internal review/correction pass, with up to 5,000 completion tokens per stage. Scores and critique remain hidden; internal card IDs and quarantined evidence are excluded from the visible answer. If Pro fails for a model/connection reason, both stages continue automatically on Flash; authentication, credit, and data-policy failures remain fail-closed. Live synthetic acceptance passed for both a two-stage Pro clarification and a two-stage Flash longitudinal answer. The latter used ten cards, 36 relations, and 20 approved source-evidence records, and returned facts, qualified hypotheses, staged actions, and limitations without another clarification round. This does not change the prohibition on live patient data or live clinical traffic.
