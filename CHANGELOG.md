# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- [2026-08-07 11:17] - Refined OpenRouter model selection scoring to properly value top-tier deepseek variants alongside GPT, and fixed UI race condition that caused conversations to reset after first question - Antigravity
- [2026-08-06 15:26] - Implemented dynamic OpenRouter model routing to optimize for Fast/Pro capabilities, automatically selecting cost-effective models while maintaining quality - Gemini 3.5 Pro
- [2026-08-06 22:21] - Expanded model whitelist to include kimi and grok, fixed UI model dropdown population bug, and corrected RTL text alignment for chat messages - Antigravity
- [2026-08-06 22:26] - Refined model routing logic to strictly prioritize price over context length. The absolute cheapest models are now selected for both Fast and Pro tiers (assuming they meet the capability threshold) - Antigravity
- [2026-08-06 23:47] - Removed the 1500 character limitation on the main chat text area (expanded to 100k) to allow pasting large case studies and long prompts - Antigravity

## [2026-08-06] Initialized knowledge base protocols.
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
[2026-08-02 12:38] - Successfully deployed application to production on Render Cloud mapped to Neo4j AuraDB. - Antigravity
[2026-08-02 12:35] - Fix UI crash on Render when local conversation DB is wiped (auto-recover lost sessions) - Gemini 3.1 Pro
[2026-08-02 15:17] - Fixed Neo4j Aura 403 error in production by implementing BoltQueryExecutor for retrieval instead of the blocked HTTP API - Gemini 2.5 Pro
[2026-08-04 15:25] - Fixed Neo4j Aura Bolt query execution and cleaned up LegacyRetrievalAdapter - Gemini 3.1 Pro
[2026-08-06 13:53] - Fixed persistent conversation loading bug in clinical_workspace_ui.py to fetch full messages, and added visual feedback (optimistic message & typing indicator) during slow API calls. - Gemini 3.1 Pro
[2026-08-06 14:04] - Added functionality to delete therapists and conversations, integrated AI for automatic conversation title generation - Gemini 3.1 Pro  
[2026-08-06 15:01] - Migrated conversation storage from local JSON file to Neo4j to support ephemeral cloud environments like Render - Gemini 3.1 Pro
 [2026-08-06 23:55] - Removed backend 1500 character limit on questions and added streaming progress indicators for the frontend to prevent users feeling stuck during long retrievals or generation. - Antigravity (Gemini)
