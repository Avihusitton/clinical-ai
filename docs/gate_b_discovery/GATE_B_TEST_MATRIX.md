# Gate B Test Matrix

## Overview
This document specifies the fixture coverage matrix for Gate B (Graph Validation & Rule Enforcement). The fixtures use synthetic, controlled, non-clinical data.

## Categories
1. **Direct Edges (Accepted/Rejected)**
2. **Two-Hop Paths (Accepted/Rejected)**

## Scenarios Covered
| Scenario | Fixture IDs | Expected Decision |
| -------- | ----------- | ----------------- |
| Approved inferential edge | `da_1` | ACCEPTED |
| Terminal relation | `da_2`, `tha_3` | ACCEPTED |
| Deterministic tie | `da_3`, `tha_4` | ACCEPTED |
| Low-degree node | `da_4`, `tha_6` | ACCEPTED |
| Allowed ordered composition | `da_5`, `tha_9` | ACCEPTED |
| Valid provenance | `da_6`, `tha_7` | ACCEPTED |
| Valid review state | `da_7`, `tha_8` | ACCEPTED |
| High-degree hub | `da_8`, `da_9`, `tha_5` | ACCEPTED |
| Exercise as bridge | `tha_1` | ACCEPTED |
| Virtual-path no-write | `tha_10` | ACCEPTED |
| Pending edge | `dr_1`, `thr_2` | REJECTED |
| Rejected edge | `dr_2`, `thr_3` | REJECTED |
| Unknown relation | `dr_3`, `thr_4` | REJECTED |
| Navigation-only relation | `dr_4`, `thr_5` | REJECTED |
| Missing provenance | `dr_5`, `thr_6` | REJECTED |
| Missing review state | `dr_6`, `thr_7` | REJECTED |
| Self-loop | `dr_7` | REJECTED |
| Cross-pilot relation | `dr_8`, `thr_8` | REJECTED |
| Out-of-scope relation | `dr_9`, `thr_9` | REJECTED |
| Blocked ordered composition | `dr_10` | REJECTED |
| Cycle | `thr_1` | REJECTED |
| Duplicate path | `thr_10` | REJECTED |
