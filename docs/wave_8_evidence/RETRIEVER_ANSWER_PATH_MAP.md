# Retriever.answer Path Map Document

**Document Status**: `VERIFIED`  
**Target Codebase**: `retrieval.py`  
**Target Method**: `Retriever.answer`  

---

## 1. Path Mapping Summary

Every return and exception path in `Retriever.answer` has been mapped to verify full coverage of shadow submission hooks:

| Path ID | Trigger Description | Legacy Operations | Legacy Return Type | Exception Type | Shadow Reached | Shadow Allowed |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **PATH-01** | No entry concept found | `find_entry_concepts` | `str` | `None` | `True` | `True` |
| **PATH-02** | Entry concept found, 0 paths | `find_entry_concepts`, `_run_reasoning` | `str` | `None` | `True` | `True` |
| **PATH-03** | Successful retrieval & compose | `find_entry_concepts`, `_run_reasoning`, `_run_exercises`, `_compose` | `str` | `None` | `True` | `True` |
| **PATH-04** | Candidate match failure | `find_entry_concepts` | `None` | `Exception` | `False` | `False` |
| **PATH-05** | Neo4j query failure | `find_entry_concepts`, `_run_reasoning` | `None` | `Exception` | `False` | `False` |
| **PATH-06** | LLM composition failure | `find_entry_concepts`, `_run_reasoning`, `_run_exercises`, `_compose` | `None` | `Exception` | `False` | `False` |

---

## 2. Invariant & Coverage Verification

1. **Successful Return Paths**: All 3 successful return paths (PATH-01, PATH-02, PATH-03) invoke `self._safe_submit_shadow(question, current_case_modality, legacy_res)` after the legacy return value `legacy_res` is computed.
2. **Exception Paths**: Exception paths (PATH-04, PATH-05, PATH-06) raise the original exception immediately, bypassing `_safe_submit_shadow` so shadow submission is never attempted when legacy processing fails.
3. **No Unhooked Early Returns**: There are no unhooked `return` statements in `Retriever.answer`.
