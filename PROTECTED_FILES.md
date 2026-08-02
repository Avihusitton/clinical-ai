# Protected Files Policy

The following files are strictly **READ-ONLY** and protected from modification, deletion, or movement without explicit owner approval:

- `retrieval.py`
- `ingestion_pipeline.py`
- `build_glossary.py`
- `run_full_pipeline.py`
- `master_dashboard.py`
- `review_app.py`
- `config.py`
- `llm_client.py`
- `relation_policy.py`
- `second_order_reasoner.py`
- `gate_c/**`
- `gate_d/**`
- `gate_cd_boundary/**`
- `controlled_integration/**`

## Security Enforcement Rules
1. Modifications to protected files require formal design freeze review and owner approval.
2. AST audit checks verify zero unauthorized imports or edits.
3. No credentials or `.env` files may be printed or modified.
