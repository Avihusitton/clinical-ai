# Evidence Reconciliation

## Overview
This document reconciles the proposed relationships with explicit repository evidence.

## Relationship Support
* **`IS_SYMPTOM_OF`**: Supported. Found in `config.py:69`, `ingestion_pipeline.py`.
* **`LEADS_TO`**: Supported. Found in `config.py:69`, `ingestion_pipeline.py`.
* **`PREVENTS`**: Supported. Found in `config.py:69`, `ingestion_pipeline.py`.
* **`IS_RECOMMENDED_FOR`**: Supported. Found in `config.py:70`, `ingestion_pipeline.py`.
* **`IS_CONTRAINDICATED_FOR`**: Supported. Found in `config.py:70`, `ingestion_pipeline.py`.
* **`WORKS_ON`**: Supported. Found in `ingestion_pipeline.py:773` (Exercise -> Concept).
* **`HAS_CANDIDATE`**: Supported. Found in `ingestion_pipeline.py:18, 755` (Chunk -> Concept/Exercise).
* **`LINKED_TO`**: Supported. Found in `ingestion_pipeline.py:17, 763` (Chunk -> Concept/Exercise).

## Contradictions & Properties
Explicit support for contradictory relations (e.g., `LEADS_TO` contradicts `PREVENTS`) or symmetric properties was **not** found in the repository evidence. These have been marked as UNKNOWN.

## Exercise Node Behavior
CURRENT_LEGACY_BEHAVIOR:
Exercise may appear as an intermediate node. This is a documented legacy defect.

PROPOSED_GATE_B_BEHAVIOR:
Exercise is terminal and may never act as an inferential bridge.
