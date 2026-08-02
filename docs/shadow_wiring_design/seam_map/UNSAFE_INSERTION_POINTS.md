# Unsafe Insertion Points Analysis (`retrieval.py`)

## Strictly Prohibited Insertion Points

1. **Inside `Retriever._run_reasoning` (lines 81–84)**:
   - **Hazard**: Modifying Cypher queries or intercepting graph traversal results before legacy synthesis.
   - **Risk**: Breaks legacy retrieval contract and corrupts theoretical concept chains.

2. **Inside `Retriever._compose` (lines 111–146)**:
   - **Hazard**: Altering system or user prompt blocks passed to LLMClient.
   - **Risk**: Violates non-autonomous formatting requirements and injects unreviewed candidates directly into LLM prompts.

3. **Global Module Scope in `retrieval.py`**:
   - **Hazard**: Initializing shadow orchestrator at module import time.
   - **Risk**: Introduces eager side effects, environment dependencies, or failure on import.

4. **Modifying `LLMClient._call` inside `llm_client.py`**:
   - **Hazard**: Intercepting or mocking LLM calls globally.
   - **Risk**: `llm_client.py` is a protected production module. Modifying it is strictly forbidden.
