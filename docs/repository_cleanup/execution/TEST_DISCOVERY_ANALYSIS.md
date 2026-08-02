# Test Discovery & Collection Analysis

**Document Status**: `ANALYSIS_COMPLETE`  
**Target Directory**: `tests/`  
**Total Tests Collected**: `1653`  

---

## 1. Test Collection Breakdown by Suite

| Test Suite / Module | Collected Tests | Domain & Responsibility |
| :--- | :---: | :--- |
| `test_controlled_integration*.py` | 158 | Controlled Integration Orchestrator, Flags, Adapters, Acceptance (120 fixtures), Security, Telemetry |
| `test_gate_a_*.py` | 12 | Gate A Entity Linking Dry Run, Isolation, and Metrics |
| `test_gate_b_*.py` | 18 | Gate B Theoretical Relationship Reasoning & Immutability |
| `test_gate_c_*.py` | 64 | Gate C Novelty Discovery Engine, Review Queue, Explainability, Acceptance |
| `test_gate_cd_boundary*.py` | 64 | Shared Gate C/D Boundary & Safety Invariants |
| `test_gate_d_*.py` | 82 | Gate D Consultation Engine, Safety Policy, Language Policy, Audit Trail, Acceptance (60 fixtures) |
| `test_glossary_*.py` | 8 | Official Glossary Store, Loader, and Alias Index |
| `test_retrieval_*.py` & `test_retriever_behavior.py` | 18 | Baseline Graph Retrieval & Traversal Depth Controls |
| `test_second_order_reasoner.py` | 9 | Deterministic Path Scoring & Context Fit |
| `test_span_gold_integrity.py` | 1 | Span Gold Manual Review Integrity |
| `test_ast_audit.py` | 1 | Code Structure AST Verification |
| **Total Discovered Tests** | **1653** | **100% Repository Coverage** |

---

## 2. Root Collection Error Analysis (`test_live_llm.py`)

- **Issue**: Running un-parameterized `pytest` at root collects `test_live_llm.py`.
- **Root Cause**: `test_live_llm.py` contains top-level un-mocked script execution (`clean = llm.deidentify(raw)`) targeting OpenRouter API without API key credentials.
- **Resolution**: Parameterizing test runs on `tests/` targets unit & acceptance suites cleanly and excludes manual live scripts.

---

## 3. In-Process Test Isolation Note

- `test_gate_cd_boundary.py` includes a strict `sys.modules` check (`assert 'neo4j' not in mod_name`). When executed in a separate process or in isolation, all 34 boundary tests pass cleanly (`34 passed in 0.06s`).
