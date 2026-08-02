# Runtime Model Alignment Audit

**Document Status**: `AUDIT_REPORT_ONLY`  
**Intended Target Model**: DeepSeek v4 Pro through OpenRouter  
**Developer Agent Model**: Gemini 3.6 Flash (Antigravity Environment)  
**Configuration Status**: No production model values modified during this audit.

---

## 1. Runtime Architecture & Call Paths

- **LLM Provider**: OpenRouter API (`https://openrouter.ai/api/v1/chat/completions`).
- **Client Implementation**: `LLMClient` in `llm_client.py`.
- **Environment Override**: `LLM_MODEL` environment variable (overrides default in `config.py`).
- **Code Fallback**: `deepseek/deepseek-v4-flash` in `config.py:Config.llm_model` (line 60).

---

## 2. Stale Model Identifier Findings

| File | Line | Current Value | Classification | Assessment | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `config.py` | 60 | `deepseek/deepseek-v4-flash` | Stale Default Fallback | Points to Flash variant rather than intended DeepSeek v4 Pro | Schedule `TASK_RUNTIME_MODEL_ALIGNMENT` to verify exact OpenRouter model slug and update default fallback |
| `GUIDE.md` | 38 | `OpenRouter` | Documentation Reference | Correct provider reference | Maintain OpenRouter reference |

---

## 3. Cost-Sensitive Call Categories & Compatibility Requirements

The pipeline executes four distinct LLM call types via `llm_client.py`:
1. `deidentify()`: Clinical text anonymization (Hebrew PII scrub). Requires high Hebrew contextual accuracy.
2. `verify_candidate()`: Entity linking binary classification (`yes`/`no`/`unclear`). Requires structured single-word compliance.
3. `classify_modality()`: Clinical modality classification (`individual`/`couples`/`family`/`general`).
4. `classify_relationship()`: Theoretical relationship extraction between concepts.

---

## 4. Planned Future Task Specification

```yaml
task_name: TASK_RUNTIME_MODEL_ALIGNMENT
target_provider: OpenRouter
target_model: DeepSeek v4 Pro
status: REQUIRES_VERIFIED_MODEL_IDENTIFIER_AND_COMPATIBILITY_TESTS
prerequisites:
  - Verify exact OpenRouter model identifier string for DeepSeek v4 Pro
  - Run structured-output compatibility test suite
  - Run Hebrew clinical de-identification benchmark suite
  - Verify temperature=0 and reasoning parameter behavior on OpenRouter
```
