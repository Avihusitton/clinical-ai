# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Initialized knowledge base protocols.
[2026-07-30 20:59] - Migrated data model and UI to a patient-centric WhatsApp-style sidebar with hierarchical conversations. Replaced user select dropdowns with patient sidebars and updated API routes accordingly - Gemini 3.1 Pro
[2026-07-31 09:07] - Refactored clinical_workspace_ui_fixed.py to use the patient-centric WhatsApp-style sidebar, fully integrated with new API routes - Antigravity
[2026-07-31 14:50] - Restored therapist workspace selector and integrated the 3-level UI hierarchy (Therapist -> Patient -> Conversation) - Antigravity
[2026-07-31 15:03] - Added edit/rename functionality for therapists and patients in UI and Backend APIs - Antigravity
[2026-07-31 16:43] - Implemented new intake pipeline to support order categorization (Primary, Secondary, Tertiary) and asynchronous ingestion of clinical material via inbox monitoring - Antigravity
[2026-07-31 17:17] - Added file upload (drag & drop PDF/Word/TXT), inbox folder scanning, and bulk file processing to the intake system - Antigravity
[2026-08-01 22:31] - Complete Legacy Code Cleanup - Gemini Pro
[2026-08-02 00:48] - Added automatic cleanup of empty directories in docs_inbox after ingestion - Gemini
[2026-08-02 01:25] - Executed Phase 2 of legacy code cleanup plan: removed LegacyRetrievalAdapter and legacy retrieval integration points - Antigravity
[2026-08-02 11:15] - Prepare for Git and Production (Docker) - Gemini Pro: Updated .gitignore, created Dockerfile, docker-compose.yml, and README.md.
