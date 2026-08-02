# Shadow Data Flow Architecture

```mermaid
flowchart TD
    A[Client Query] --> B[retrieval.py: Retriever.answer]
    B --> C[Execute Legacy Retrieval & LLM]
    C --> D[Legacy Result String]
    D --> E{Feature Flag: SHADOW_COMPARE?}
    E -- No / Emergency Disabled --> F[Return Legacy Result to Client]
    E -- Yes --> G[Build Redacted Shadow Input]
    G --> H[Submit Task to Local Bounded Queue]
    H --> F
    H -- Asynchronous Background Worker --> I[Isolated IntegrationOrchestrator]
    I --> J{Shadow Success?}
    J -- Exception / Timeout / Queue Full --> K[Log SHADOW_ERROR / TIMEOUT / SATURATED]
    J -- Success --> L[ShadowComparison Engine]
    L --> M[Record Audit & Telemetry]
    K --> N[Discard Shadow Payload]
    M --> N
```

## Privacy & Redaction Boundaries

1. **Input Sanitization**: User IDs are hashed with salted SHA-256 (`sha256:{hash}`). Query text is sanitized via `SecurityPolicy.scan_pii()` with specific regex patterns for Israeli PII (ID numbers, 05x/0x/972 phones, HMO IDs, case files).
2. **Execution Strategy**: `OFF_CRITICAL_PATH_SHADOW`. Legacy result is returned immediately without waiting for background shadow comparison.
3. **Queue Saturation**: Under heavy load, tasks are dropped cleanly (`DROP_SHADOW_TASK_AND_AUDIT`) without queuing delays or retries on the request thread.
