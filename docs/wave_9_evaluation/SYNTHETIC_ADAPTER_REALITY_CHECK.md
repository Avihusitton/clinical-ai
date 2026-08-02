# Synthetic Adapter Reality Check Report

> [!IMPORTANT]
> Synthetic adapter output is plumbing evidence only. It is not evidence of real clinical retrieval or knowledge quality.

## Overview

This document inspects all 5 adapters in the `controlled_integration` package to clarify their offline synthetic boundaries. None of these adapters connect to external APIs, live Neo4j databases, or live LLM services during offline Wave 9 evaluation.

## Adapter Inventory and Accounting

### 1. `LegacyRetrievalAdapter`
- **Real Input Dependency**: `retrieval.Retriever`, Neo4j graph session, LLM client.
- **Synthetic Default Present**: `true`
- **Hardcoded Value Present**: `true`
- **External Service Required**: `false`
- **Eligible for Offline Evaluation**: `true`
- **Limitations**: Uses mocked Retriever and mock cypher query results for offline execution.

### 2. `GateBAdapter`
- **Real Input Dependency**: `models.relation_policy`, `models.second_order_reasoner`.
- **Synthetic Default Present**: `true`
- **Hardcoded Value Present**: `true`
- **External Service Required**: `false`
- **Eligible for Offline Evaluation**: `true`
- **Limitations**: Evaluates mock relation policy definitions and synthetic evidence bundles.

### 3. `GateCAdapter`
- **Real Input Dependency**: `gate_c.novelty_engine`.
- **Synthetic Default Present**: `true`
- **Hardcoded Value Present**: `true`
- **External Service Required**: `false`
- **Eligible for Offline Evaluation**: `true`
- **Limitations**: Evaluates synthetic novelty discovery candidates without live graph persistence.

### 4. `BoundaryAdapter`
- **Real Input Dependency**: `gate_cd_boundary.evidence_eligibility`.
- **Synthetic Default Present**: `true`
- **Hardcoded Value Present**: `false`
- **External Service Required**: `false`
- **Eligible for Offline Evaluation**: `true`
- **Limitations**: Filters reviewed vs unreviewed novelty using synthetic eligibility rules.

### 5. `GateDAdapter`
- **Real Input Dependency**: `gate_d.consultation_engine`.
- **Synthetic Default Present**: `true`
- **Hardcoded Value Present**: `true`
- **External Service Required**: `false`
- **Eligible for Offline Evaluation**: `true`
- **Limitations**: Executes consultation synthesis using offline rule engine without external LLM calls.

---
*Generated for Wave 9 Offline Synthetic Shadow Evaluation.*
