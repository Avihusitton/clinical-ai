# Local Method Q&A Runbook

## Scope

This runbook covers the local, read-only method-knowledge interface backed by the signed D4 dictionary release. It does not authorize live patient data, live clinical traffic, production Neo4j writes, or clinical recommendations.

## Start

Run:

```powershell
& 'C:\Avihusitton\clinical_ai\start_local_system.ps1'
```

The launcher:

1. Verifies the exact local Neo4j Desktop instance and bundled Java runtime.
2. Starts Neo4j in console mode only when Bolt is not already listening.
3. Starts the local Q&A service on loopback only.
4. Writes process and health evidence under `out/local_runtime/`.
5. Ignores the exposed legacy credential and reads AI settings only from the
   dedicated ignored secret file or dedicated process variables.

## Open

Use:

```text
http://127.0.0.1:8765
```

The UI accepts method-knowledge questions only. The user must confirm that no
patient or identified-person data is included. Canonical cards and graph
relations are collapsed under an evidence disclosure rather than shown as the
primary answer.

## Optional AI answer

The default remains deterministic and local. To enable the opt-in checkbox:

1. Rotate the previously exposed OpenRouter key.
2. Open the ignored local file:

```text
C:\Avihusitton\clinical_ai\.secrets\openrouter.env
```

3. Replace only `PASTE_NEW_ROTATED_KEY_HERE` with the new key.
4. Refresh the application page. No source-code edit or service restart is
   required.

The application reads the key in memory and never returns it in health, answer,
or log output. It does not read `OPENROUTER_API_KEY` from the legacy root `.env`
or from the ordinary process environment.

When selected, the graph retrieves canonical grounding first. Long case-style
questions use balanced retrieval lenses and can select up to ten approved D4
cards. Each card may contribute the unified definition, source-based definition,
short example, common mistakes, approved relations, and `METHOD_PRIMARY`
evidence locators. The context is capped at 32,000 characters and output at 5,000
completion tokens per stage.

For a short follow-up such as "continue from what was already provided",
retrieval also uses up to the three latest user-authored updates. Assistant text
is not added to the retrieval query. After one clarification round, a concrete
update plus an explicit request for direction produces a provisional, qualified
answer; remaining gaps are listed as limitations instead of creating an endless
clarification loop.

The AI path has two stages:

1. Evidence-grounded analysis and draft: stated facts, missing information,
   tensions, relevant lenses, canonical basis, and explicitly marked hypotheses.
2. Independent internal review and correction for fidelity, over-inference,
   clarification quality, usefulness, clarity, and proportionality.

The reviewer score and critique are never shown to the user. Only the corrected
answer is displayed. Quarantined evidence is not queried by runtime retrieval,
not stored in conversation evidence, and never sent to either AI stage.

The UI offers quality-first `deepseek/deepseek-v4-pro` and speed/cost-first
`deepseek/deepseek-v4-flash`; Pro is the default selection. Provider routing
requests deny data collection. On first-stage AI failure, the application falls
back from Pro to Flash automatically when the failure is model/connection
related. Authentication, credit, and data-policy failures remain fail-closed. If
both models fail, the deterministic result is used. If only the reviewer fails,
the grounded draft is returned with an internal-review warning.

## Answer Contract

- Mode: `D4_CANONICAL_LOCAL_READ_ONLY`
- Canonical layer: approved `DictionaryEntity:GlossaryEntry` records from release `D4-99F53565A7BCC45E`
- Canonical relations: approved D4 relation types only
- Approved source evidence: `METHOD_PRIMARY` locators only
- Quarantine layer: excluded from runtime retrieval and conversation evidence
- LLM calls: none by default; two opt-in calls (draft and internal review) when
  a dedicated key is configured
- External network calls: none by default; opt-in OpenRouter call only
- Neo4j mutation: forbidden by the client

## Acceptance Evidence

- Dedicated secret detected without exposing its value: `PASS`
- Live synthetic DeepSeek V4 Pro request: `PASS_TWO_STAGE_REVIEWED`
- Rich grounding contract: up to 32,000 context characters / 10 cards /
  36 approved relations / approved source locators
- Observed clarification request: 26,683 context characters / 10 cards /
  36 relations / 19 approved source-evidence records
- Observed generation: two stages / 24,687 prompt tokens /
  5,925 completion tokens / 138,286 ms / estimated visible cost `₪0.0728`
- Observed longitudinal answer after clarification: `PASS` / Flash / two
  stages / 10 cards / 36 relations / 20 source-evidence records /
  26,772 context characters / 188,028 ms / visible cost `₪0.0140`
- Longitudinal answer contract: facts, qualified hypotheses, staged actions,
  and limitations returned without another clarification round
- Visible answer redaction: no internal card ID and no reviewer score
- Focused runtime regression suite: 41 / 41 tests passed
- Live AI response completion: `PASS`
- Health endpoint: `PASS`
- A002 query: `עצמאות רגשית`
- A008 longest-phrase query: `הרחבת המסוגלות`
- Privacy confirmation gate: `PASS`
- Direct-identifier block: `PASS`
- Graph before: 1,125 nodes / 8,093 relationships
- Graph after: 1,125 nodes / 8,093 relationships
- Browser RTL and right alignment: `PASS`
- Browser console errors or warnings: zero

## Runtime Evidence

```text
C:\Avihusitton\clinical_ai\out\local_runtime\runtime_status.json
C:\Avihusitton\clinical_ai\out\local_runtime\e2e_acceptance.json
```

## Recovery

The Q&A process ID is stored in `out/local_runtime/local_qa.pid`. Neo4j's tracking file was backed up before reconciliation:

```text
C:\Users\avihu\.Neo4jDesktop2\Data\dbmss\dbms-07f6d302-9c7c-4f1f-95bf-201f9ebf8e9a\run\neo4j-relate.pid.pre-reconcile-20260729-140501.bak
```

Do not delete graph data or run batch rollback for a UI/runtime issue. Restart the local launcher first.
