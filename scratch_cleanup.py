import os
import shutil

root = r'C:\Avihusitton\clinical_ai'
arch = os.path.join(root, '_archived_legacy')

def safe_move(src_rel, dst_rel):
    src = os.path.join(root, src_rel)
    dst = os.path.join(arch, dst_rel)
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        print(f'Moved {src_rel} to archive')

# orphan scripts
orphans = [
    'activate_lexicons.py', 'auto_ingest_loop.py', 'backfill_relationships.py',
    'benchmark_trie.py', 'check_neo4j_ready.py', 'cleanup_shadow.py',
    'curate_glossary.py', 'diagnose_docx.py', 'document_types_inspector.py',
    'generate_gate_b_contracts.py', 'load_approved_relationships.py',
    'master_dashboard.py', 'neo4j_after_load.py', 'neo4j_baseline.py',
    'neo4j_before_load.py', 'neo4j_diagnose_duplicates.py', 'neo4j_full_status.py',
    'neo4j_target_static_audit.py', 'prepare_preflight.py', 'recover_ui.py',
    'recovered_lines.py', 'refactor_ui.py', 'refine_drafts.py',
    'reset_environment.py', 'restore_draft.py', 'review_app.py',
    'review_glossary.py', 'review_glossary_app.py', 'run_all.py',
    'run_full_pipeline.py', 'setup.py', 'stitch.py',
    'test_candidate_matching.py', 'test_live_llm.py', 'track_progress.py',
    'wait_for_files.py'
]

for o in orphans:
    safe_move(o, f'orphan_scripts/{o}')

# legacy test files
legacy_tests = [
    'tests/test_controlled_integration_fallback.py',
    'tests/test_shadow_wiring_dispatcher.py'
]

for t in legacy_tests:
    safe_move(t, t)

# remove the original legacy_adapter if it exists since we copied it
try:
    os.remove(os.path.join(root, 'controlled_integration/adapters/legacy_adapter.py'))
except Exception:
    pass

print('Done')
