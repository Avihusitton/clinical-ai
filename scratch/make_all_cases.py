import json
import os

cases = []

# 1. Legacy-only (20 cases)
legacy_topics = [
    "CBT depression intervention step 1 protocol",
    "GAD-7 assessment scoring protocol reference",
    "Behavioral activation activity scheduling protocol",
    "Exposure therapy hierarchy creation guidelines",
    "Mindfulness-based stress reduction protocol step 3",
    "Sleep hygiene psychoeducation protocol",
    "Panic disorder interoceptive exposure protocol",
    "Social anxiety behavioral experiment guidelines",
    "Distress tolerance TIPP skills protocol",
    "Emotion regulation DEAR MAN communication protocol",
    "ACT values clarification exercise guidelines",
    "Relapse prevention plan drafting protocol",
    "Problem-solving therapy 5-step framework",
    "Progressive muscle relaxation script protocol",
    "Grounding techniques 5-4-3-2-1 protocol",
    "Thought record tracking format reference",
    "Behavioral chain analysis protocol",
    "Motivational interviewing OARS framework",
    "Safety planning intervention Stanley-Brown protocol",
    "Clinical session summary documentation template"
]

for idx, topic in enumerate(legacy_topics, 1):
    case_num = f"{idx:03d}"
    cases.append({
        "case_id": f"SYN-LEG-{case_num}",
        "operating_mode": "legacy_only",
        "synthetic_request": {
            "request_id": f"REQ-SYN-LEG-{case_num}",
            "query": f"Synthetic protocol query: {topic}",
            "user_role": "licensed_therapist",
            "session_context": {"facility_id": "SYN-FAC-01", "environment": "internal_pilot"}
        },
        "feature_flags": {
            "master_pilot_flag": True,
            "shadow_mode_enabled": False,
            "graph_rag_enabled": False,
            "strict_provenance_enforced": True,
            "novelty_blocking_enabled": True,
            "legacy_fallback_enabled": True
        },
        "available_official_evidence": [
            {
                "evidence_id": f"EV-LEG-{100+idx}",
                "source": f"Official_Guideline_DB_{2024 + (idx%2)}",
                "confidence_score": round(0.92 + (idx % 8) * 0.01, 2),
                "verified_status": "official",
                "content_summary": f"Established clinical protocol guidelines for {topic}."
            }
        ],
        "available_reviewed_relations": [],
        "available_novelty": [],
        "expected_components_called": ["legacy_retrieval_engine", "security_policy_enforcer", "audit_logger"],
        "expected_components_blocked": ["graph_rag_retriever", "novelty_filter"],
        "expected_output_type": "legacy_guideline_response",
        "expected_fallback": {"triggered": False, "reason": None, "fallback_component": None},
        "expected_audit_events": ["AUDIT_REQUEST_RECEIVED", "AUDIT_LEGACY_FETCH_SUCCESS", "AUDIT_RESPONSE_DELIVERED"],
        "expected_security_result": {"passed": True, "reason": "Authorized legacy access under master pilot flag", "block_type": None}
    })

# 2. Shadow-comparison (20 cases)
shadow_topics = [
    "CBT depression vs GraphRAG relation retrieval comparison",
    "Anxiety intervention graph traversal vs legacy vector search",
    "PTSD prolonged exposure protocol graph mapping comparison",
    "OCD ERP protocol graph evidence lookup validation",
    "Insomnia CBT-I restriction protocol graph lookup benchmark",
    "Bipolar psychoeducation graph relation mapping comparison",
    "Panic disorder cognitive therapy graph traversal evaluation",
    "Phobia systematic desensitization graph vs legacy comparison",
    "Chronic pain CBT management graph mapping benchmark",
    "Grief therapy dual process model graph lookup evaluation",
    "Anger management cognitive restructuring graph comparison",
    "Health anxiety symptom checking graph traversal benchmark",
    "AUDIT assessment protocol graph vs legacy lookup",
    "Eating disorder CBT-E psychoeducation graph mapping benchmark",
    "Trauma-informed care principles graph lookup evaluation",
    "Caregiver stress psychoeducation graph traversal comparison",
    "Post-partum anxiety CBT graph relation mapping benchmark",
    "Adjustment disorder coping skills graph vs legacy evaluation",
    "ADHD executive function psychoeducation graph mapping test",
    "Somatization CBT psychoeducation graph lookup comparison"
]

for idx, topic in enumerate(shadow_topics, 1):
    case_num = f"{idx:03d}"
    cases.append({
        "case_id": f"SYN-SHD-{case_num}",
        "operating_mode": "shadow_comparison",
        "synthetic_request": {
            "request_id": f"REQ-SYN-SHD-{case_num}",
            "query": f"Shadow comparison query: {topic}",
            "user_role": "licensed_therapist",
            "session_context": {"facility_id": "SYN-FAC-01", "environment": "internal_pilot"}
        },
        "feature_flags": {
            "master_pilot_flag": True,
            "shadow_mode_enabled": True,
            "graph_rag_enabled": True,
            "strict_provenance_enforced": True,
            "novelty_blocking_enabled": True,
            "legacy_fallback_enabled": True
        },
        "available_official_evidence": [
            {
                "evidence_id": f"EV-SHD-{200+idx}",
                "source": "DSM5_Synthetic_Guideline_Ref",
                "confidence_score": round(0.94 + (idx % 5) * 0.01, 2),
                "verified_status": "official",
                "content_summary": f"Official guidelines reference for {topic}."
            }
        ],
        "available_reviewed_relations": [
            {
                "relation_id": f"REL-SHD-{200+idx}",
                "source_node": f"Clinical_Concept_{idx}",
                "target_node": f"Intervention_Modality_{idx}",
                "relation_type": "INDICATED_FOR",
                "review_status": "reviewed",
                "evidence_link": f"EV-SHD-{200+idx}"
            }
        ],
        "available_novelty": [],
        "expected_components_called": ["legacy_retrieval_engine", "graph_rag_retriever", "shadow_comparator", "provenance_validator", "audit_logger"],
        "expected_components_blocked": ["user_facing_graph_synthesizer"],
        "expected_output_type": "shadow_comparison_log",
        "expected_fallback": {"triggered": False, "reason": None, "fallback_component": None},
        "expected_audit_events": ["AUDIT_REQUEST_RECEIVED", "AUDIT_LEGACY_FETCH", "AUDIT_SHADOW_GRAPH_FETCH", "AUDIT_COMPARISON_LOGGED", "AUDIT_RESPONSE_DELIVERED"],
        "expected_security_result": {"passed": True, "reason": "Shadow mode executed silently without user risk", "block_type": None}
    })

# 3. Reviewed-evidence consultation (20 cases)
reviewed_topics = [
    "CBT depression step 2 with verified evidence provenance",
    "GAD cognitive restructuring with reviewed relation mapping",
    "PTSD trauma memory processing with verified source citations",
    "OCD exposure hierarchy design with reviewed graph evidence",
    "CBT-I sleep restriction schedule with verified evidence provenance",
    "Panic disorder breathing retraining with reviewed relation mapping",
    "Social anxiety video feedback protocol with verified citations",
    "DBT distress tolerance self-soothing with reviewed graph evidence",
    "ACT cognitive defusion exercise with verified evidence provenance",
    "Behavioral activation reward scheduling with reviewed relation mapping",
    "Health anxiety exposure protocol with verified source citations",
    "Chronic pain pacing protocol with reviewed graph evidence",
    "Anger management physiological awareness with verified provenance",
    "Relapse prevention trigger identification with reviewed relations",
    "Depression cognitive triad identification with verified source citations",
    "Mindfulness body scan protocol with reviewed graph evidence",
    "Problem-solving therapy decision matrix with verified provenance",
    "Motivational interviewing decisional balance with reviewed relations",
    "Trauma-informed grounding protocol with verified source citations",
    "Sleep hygiene stimulus control with reviewed graph evidence"
]

for idx, topic in enumerate(reviewed_topics, 1):
    case_num = f"{idx:03d}"
    cases.append({
        "case_id": f"SYN-REV-{case_num}",
        "operating_mode": "reviewed_consultation",
        "synthetic_request": {
            "request_id": f"REQ-SYN-REV-{case_num}",
            "query": f"Active consultation query: {topic}",
            "user_role": "licensed_therapist",
            "session_context": {"facility_id": "SYN-FAC-01", "environment": "internal_pilot"}
        },
        "feature_flags": {
            "master_pilot_flag": True,
            "shadow_mode_enabled": False,
            "graph_rag_enabled": True,
            "strict_provenance_enforced": True,
            "novelty_blocking_enabled": True,
            "legacy_fallback_enabled": True
        },
        "available_official_evidence": [
            {
                "evidence_id": f"EV-REV-{300+idx}",
                "source": "NICE_Synthetic_Clinical_Guideline",
                "confidence_score": round(0.95 + (idx % 4) * 0.01, 2),
                "verified_status": "official",
                "content_summary": f"Peer-reviewed evidence summary supporting {topic}."
            }
        ],
        "available_reviewed_relations": [
            {
                "relation_id": f"REL-REV-{300+idx}",
                "source_node": f"Symptom_Cluster_{idx}",
                "target_node": f"Therapeutic_Protocol_{idx}",
                "relation_type": "RECOMMENDED_BY_EVIDENCE",
                "review_status": "reviewed",
                "evidence_link": f"EV-REV-{300+idx}"
            }
        ],
        "available_novelty": [],
        "expected_components_called": ["graph_rag_retriever", "provenance_validator", "uncertainty_calculator", "ui_provenance_formatter", "audit_logger"],
        "expected_components_blocked": ["novelty_filter"],
        "expected_output_type": "reviewed_evidence_response",
        "expected_fallback": {"triggered": False, "reason": None, "fallback_component": None},
        "expected_audit_events": ["AUDIT_REQUEST_RECEIVED", "AUDIT_GRAPH_FETCH_SUCCESS", "AUDIT_PROVENANCE_VERIFIED", "AUDIT_UNCERTAINTY_CALCULATED", "AUDIT_RESPONSE_DELIVERED"],
        "expected_security_result": {"passed": True, "reason": "All relations reviewed and verified against official evidence", "block_type": None}
    })

# 4. Blocked novelty (20 cases)
novelty_topics = [
    "Unreviewed drug-herb interaction hypothesis in depression",
    "Unverified experimental neuromodulation protocol relation",
    "Unreviewed off-label pharmacological augmentation link",
    "Novel unvalidated somatic intervention hypothesis",
    "Unreviewed dietary supplement clinical linkage",
    "Experimental biofeedback protocol unverified relation",
    "Novel unverified diagnostic subtype classification relation",
    "Unreviewed alternative therapy linkage during graph traversal",
    "Novel experimental psychedelic-assisted therapy relation",
    "Unverified rapid desensitization variant relation",
    "Novel unreviewed genetic biomarker relation",
    "Unverified digital therapeutics app interaction relation",
    "Novel unvalidated herbal extract combination link",
    "Unreviewed high-dose exercise protocol augmentation relation",
    "Novel experimental light therapy schedule relation",
    "Unverified vagus nerve stimulation clinical link",
    "Novel unreviewed acupuncture protocol relation",
    "Unvalidated neurofeedback frequency relation",
    "Novel experimental sleep deprivation protocol relation",
    "Unreviewed hyperbaric therapy linkage"
]

for idx, topic in enumerate(novelty_topics, 1):
    case_num = f"{idx:03d}"
    cases.append({
        "case_id": f"SYN-NOV-{case_num}",
        "operating_mode": "blocked_novelty",
        "synthetic_request": {
            "request_id": f"REQ-SYN-NOV-{case_num}",
            "query": f"Synthetic clinical query introducing novelty: {topic}",
            "user_role": "licensed_therapist",
            "session_context": {"facility_id": "SYN-FAC-01", "environment": "internal_pilot"}
        },
        "feature_flags": {
            "master_pilot_flag": True,
            "shadow_mode_enabled": False,
            "graph_rag_enabled": True,
            "strict_provenance_enforced": True,
            "novelty_blocking_enabled": True,
            "legacy_fallback_enabled": True
        },
        "available_official_evidence": [
            {
                "evidence_id": f"EV-NOV-{400+idx}",
                "source": "Standard_Base_Guideline_Ref",
                "confidence_score": 0.86,
                "verified_status": "official",
                "content_summary": "Standard baseline protocol without unreviewed additions."
            }
        ],
        "available_reviewed_relations": [],
        "available_novelty": [
            {
                "novelty_id": f"NOV-UNR-{400+idx}",
                "description": f"Unreviewed relation candidate: {topic}",
                "review_status": "unreviewed",
                "risk_score": round(0.80 + (idx % 15) * 0.01, 2)
            }
        ],
        "expected_components_called": ["graph_rag_retriever", "novelty_filter", "security_policy_enforcer", "audit_logger"],
        "expected_components_blocked": ["unreviewed_relation_synthesizer", "novel_hypothesis_output"],
        "expected_output_type": "novelty_blocked_notice",
        "expected_fallback": {"triggered": True, "reason": "Novelty policy violation: unreviewed relation detected", "fallback_component": "legacy_retrieval_engine"},
        "expected_audit_events": ["AUDIT_REQUEST_RECEIVED", "AUDIT_GRAPH_FETCH", "AUDIT_NOVELTY_DETECTED", "AUDIT_NOVELTY_BLOCKED", "AUDIT_FALLBACK_TRIGGERED", "AUDIT_RESPONSE_DELIVERED"],
        "expected_security_result": {"passed": True, "reason": "Unreviewed novelty intercepted and blocked by governance policy", "block_type": "NOVELTY_BLOCK"}
    })

# 5. Fallback/error (20 cases)
error_topics = [
    "Graph DB network timeout during query execution",
    "Vector store index connection refusal error",
    "GraphRAG response schema validation failure",
    "Empty graph node traversal result exception",
    "Knowledge graph service HTTP 503 unavailable error",
    "Provenance validator service internal exception",
    "Uncertainty calculator floating point overflow error",
    "Graph Cypher query syntax parsing exception",
    "Vector embedding service API rate limit exceeded",
    "Graph DB connection pool exhaustion error",
    "Synthesis LLM context response truncation error",
    "Memory buffer boundary check failure detection",
    "Subsystem heartbeat signal loss detection",
    "Graph relation JSON deserialization schema mismatch",
    "Dependency graph health check ping timeout",
    "Vector similarity metric distance calculation failure",
    "Subsystem response latency SLA breach (>3000ms)",
    "Graph node required property missing exception",
    "Synthesis engine token window overflow exception",
    "Circuit breaker tripped on graph service failure"
]

for idx, topic in enumerate(error_topics, 1):
    case_num = f"{idx:03d}"
    cases.append({
        "case_id": f"SYN-ERR-{case_num}",
        "operating_mode": "fallback_error",
        "synthetic_request": {
            "request_id": f"REQ-SYN-ERR-{case_num}",
            "query": f"Synthetic query during subsystem fault: {topic}",
            "user_role": "licensed_therapist",
            "session_context": {"facility_id": "SYN-FAC-01", "environment": "internal_pilot"}
        },
        "feature_flags": {
            "master_pilot_flag": True,
            "shadow_mode_enabled": False,
            "graph_rag_enabled": True,
            "strict_provenance_enforced": True,
            "novelty_blocking_enabled": True,
            "legacy_fallback_enabled": True
        },
        "available_official_evidence": [],
        "available_reviewed_relations": [],
        "available_novelty": [],
        "expected_components_called": ["graph_rag_retriever", "fallback_orchestrator", "legacy_retrieval_engine", "audit_logger"],
        "expected_components_blocked": ["graph_rag_synthesizer"],
        "expected_output_type": "deterministic_fallback_response",
        "expected_fallback": {"triggered": True, "reason": f"System fault detected: {topic}", "fallback_component": "legacy_retrieval_engine"},
        "expected_audit_events": ["AUDIT_REQUEST_RECEIVED", "AUDIT_GRAPH_FETCH_FAILED", "AUDIT_FALLBACK_TRIGGERED", "AUDIT_LEGACY_FETCH_SUCCESS", "AUDIT_RESPONSE_DELIVERED"],
        "expected_security_result": {"passed": True, "reason": "Safe fallback executed cleanly without patient risk", "block_type": None}
    })

# 6. Security/governance (20 cases)
security_topics = [
    ("Request from unauthorized role (guest)", "unauthorized_guest", "RBAC_ROLE_VIOLATION"),
    ("Synthetic PII string pattern (MRN in query)", "licensed_therapist", "PII_PATTERN_DETECTED"),
    ("Attempt to override feature flag in payload", "licensed_therapist", "FEATURE_FLAG_TAMPERING"),
    ("Query submitted during emergency kill-switch state", "licensed_therapist", "KILL_SWITCH_ACTIVE"),
    ("Unauthenticated request header missing JWT token", "unauthenticated", "AUTH_TOKEN_MISSING"),
    ("Unauthorized therapist accessing restricted clinical domain", "licensed_therapist_unassigned", "RBAC_DOMAIN_RESTRICTION"),
    ("SQL/Cypher injection pattern in query string", "licensed_therapist", "INJECTION_PATTERN_DETECTED"),
    ("Malformed session token signature", "invalid_session", "INVALID_TOKEN_SIGNATURE"),
    ("Attempt to disable audit logging in request metadata", "licensed_therapist", "AUDIT_TAMPERING_ATTEMPT"),
    ("Rate limit threshold breach (burst requests)", "licensed_therapist", "RATE_LIMIT_EXCEEDED"),
    ("Synthetic patient identifier string in query", "licensed_therapist", "PII_PATTERN_DETECTED"),
    ("Request attempting privilege escalation to admin role", "licensed_therapist", "PRIVILEGE_ESCALATION_ATTEMPT"),
    ("Attempt to access raw unmasked database endpoint", "licensed_therapist", "RAW_DB_ACCESS_DENIED"),
    ("Synthetic phone/email string in query", "licensed_therapist", "PII_PATTERN_DETECTED"),
    ("Invalid digital signature on payload header", "licensed_therapist", "PAYLOAD_SIGNATURE_INVALID"),
    ("Expired session credential request", "expired_user", "SESSION_EXPIRED"),
    ("Cross-tenant context leakage attempt", "licensed_therapist", "CROSS_TENANT_VIOLATION"),
    ("Synthetic SSN pattern in query payload", "licensed_therapist", "PII_PATTERN_DETECTED"),
    ("Unauthorized system API key attempt", "external_bot", "UNAUTHORIZED_API_KEY"),
    ("Master pilot flag disabled request", "licensed_therapist", "PILOT_FLAG_DISABLED")
]

for idx, (topic, role, block_code) in enumerate(security_topics, 1):
    case_num = f"{idx:03d}"
    cases.append({
        "case_id": f"SYN-SEC-{case_num}",
        "operating_mode": "security_governance",
        "synthetic_request": {
            "request_id": f"REQ-SYN-SEC-{case_num}",
            "query": f"Synthetic security test: {topic}",
            "user_role": role,
            "session_context": {"facility_id": "SYN-FAC-01", "environment": "internal_pilot"}
        },
        "feature_flags": {
            "master_pilot_flag": False if block_code == "PILOT_FLAG_DISABLED" else True,
            "shadow_mode_enabled": False,
            "graph_rag_enabled": True,
            "strict_provenance_enforced": True,
            "novelty_blocking_enabled": True,
            "legacy_fallback_enabled": True
        },
        "available_official_evidence": [],
        "available_reviewed_relations": [],
        "available_novelty": [],
        "expected_components_called": ["security_policy_enforcer", "audit_logger"],
        "expected_components_blocked": ["graph_rag_retriever", "legacy_retrieval_engine", "synthesis_engine"],
        "expected_output_type": "security_denial_audit",
        "expected_fallback": {"triggered": False, "reason": "Security violation halts processing immediately", "fallback_component": None},
        "expected_audit_events": ["AUDIT_REQUEST_RECEIVED", "AUDIT_SECURITY_VIOLATION_DETECTED", "AUDIT_REQUEST_DENIED", "AUDIT_ALERT_TRIGGERED"],
        "expected_security_result": {"passed": False, "reason": f"Access denied due to governance constraint: {block_code}", "block_type": block_code}
    })

out_path = os.path.join("tests", "fixtures", "integration_design", "integration_cases.jsonl")
with open(out_path, "w", encoding="utf-8") as f:
    for c in cases:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

print(f"Successfully generated {len(cases)} cases into {out_path}")
