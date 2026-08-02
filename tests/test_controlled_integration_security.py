"""
tests/test_controlled_integration_security.py
-----------------------------------------------
Unit tests for security policy, RBAC authorization, PII detection/rejection, and narrative storage rules.
Verifies security boundary enforcement and zero raw PII storage constraints.
"""

import pytest
from controlled_integration.security import (
    SecurityPolicy,
    PIIRejectedError,
    AccessDeniedError,
    RawNarrativeStoreForbiddenError,
)
from controlled_integration.adapters.boundary_adapter import BoundaryAdapter
from controlled_integration.models import (
    OfficialEvidenceBundle,
    NoveltyDiscoveryBundle,
)
from controlled_integration.exceptions import UnreviewedNoveltyLeakError


def test_pii_detection_and_rejection():
    """Verify SecurityPolicy detects PII patterns and raises PIIRejectedError."""
    policy = SecurityPolicy()

    pii_samples = [
        "Patient SSN is 123-45-6789 for consultation",
        "Contact email at patient.john@example.com",
        "US phone number 555-123-4567 in notes",
        "Israeli phone number 054-123-4567 in record",
        "Patient MRN: 987654321 clinical query",
    ]

    for pii_text in pii_samples:
        with pytest.raises(PIIRejectedError) as exc_info:
            policy.validate_input(pii_text)
        assert "PII detected in request" in str(exc_info.value)


def test_clean_text_passes_pii_validation():
    """Verify synthetic clinical queries without PII pass validation."""
    policy = SecurityPolicy()
    clean_queries = [
        "Synthetic protocol query: CBT depression intervention step 1 protocol",
        "GAD-7 assessment scoring protocol reference",
        "Exposure therapy hierarchy creation guidelines",
    ]
    for clean_text in clean_queries:
        policy.validate_input(clean_text)  # Should not raise exception
        assert len(policy.scan_pii(clean_text)) == 0


def test_pii_sanitization():
    """Verify SecurityPolicy.sanitize_text redacts PII strings."""
    text_with_pii = "Contact john@hospital.org or call 555-987-6543 for SSN 999-88-7777."
    sanitized = SecurityPolicy.sanitize_text(text_with_pii)
    assert "[REDACTED_EMAIL]" in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "[REDACTED_SSN]" in sanitized
    assert "john@hospital.org" not in sanitized


def test_rbac_role_authorization_allowed_roles():
    """Verify authorized roles pass RBAC check for pilot resources."""
    policy = SecurityPolicy()

    authorized_roles = [
        "ROLE_INTERNAL_THERAPIST",
        "THERAPIST_PILOT_USER",
    ]

    for role in authorized_roles:
        res = policy.check_access(user_role=role, resource_id="pilot_query_advisor")
        assert res is True


def test_rbac_role_authorization_denied_roles():
    """Verify unauthorized roles raise AccessDeniedError."""
    policy = SecurityPolicy()

    unauthorized_roles = [
        "unauthorized_guest",
        "unauthenticated",
        "unknown_role",
        "ROLE_GUEST",
    ]

    for role in unauthorized_roles:
        with pytest.raises(AccessDeniedError) as exc_info:
            policy.check_access(user_role=role, resource_id="pilot_query_advisor")
        assert "is denied access to resource" in str(exc_info.value)


def test_knowledge_graph_write_explicit_deny():
    """Verify knowledge_graph_write is explicitly denied for ALL roles."""
    policy = SecurityPolicy()
    all_roles = [
        "ROLE_INTERNAL_THERAPIST",
        "THERAPIST_PILOT_USER",
        "ROLE_CLINICAL_REVIEWER",
        "SYSTEM_OPERATOR",
        "SECURITY_AUDITOR",
    ]
    for role in all_roles:
        with pytest.raises(AccessDeniedError):
            policy.check_access(user_role=role, resource_id="knowledge_graph_write")


def test_raw_narrative_storage_forbidden():
    """Verify raw clinical narrative storage is strictly forbidden."""
    policy = SecurityPolicy()
    with pytest.raises(RawNarrativeStoreForbiddenError):
        policy.validate_narrative_storage(store_raw_narrative=True)

    policy.validate_narrative_storage(store_raw_narrative=False)  # Should pass


def test_gate_cd_boundary_novelty_interception():
    """Verify Gate C/D boundary screens out unreviewed novelty candidates."""
    boundary = BoundaryAdapter()
    official = OfficialEvidenceBundle(
        bundle_id="b_sec",
        official_entries=[{"source_id": "OFF_01", "is_approved": True, "is_reviewed": True}],
    )
    novelty = NoveltyDiscoveryBundle(
        bundle_id="n_sec",
        candidates=[
            {
                "candidate_id": "NOV_UNR_01",
                "status": "DISCOVERY_ONLY",
                "review_status": "PENDING_HUMAN_REVIEW",
            }
        ],
    )

    bundle = boundary.filter_for_consultation("sess_sec", official, novelty)
    assert bundle.blocked_novelty_count == 1
    assert len(bundle.eligible_official_evidence) == 1


def test_gate_cd_boundary_forced_leak_exception():
    """Verify forced leak of unreviewed novelty raises UnreviewedNoveltyLeakError."""
    boundary = BoundaryAdapter()
    official = OfficialEvidenceBundle(bundle_id="b_leak")
    novelty = NoveltyDiscoveryBundle(
        bundle_id="n_leak",
        candidates=[
            {
                "candidate_id": "NOV_LEAK_01",
                "status": "DISCOVERY_ONLY",
                "review_status": "PENDING_HUMAN_REVIEW",
                "force_leak": True,
            }
        ],
    )

    with pytest.raises(UnreviewedNoveltyLeakError) as exc_info:
        boundary.filter_for_consultation("sess_leak", official, novelty)
    assert "Candidate 'NOV_LEAK_01' blocked from crossing boundary" in str(exc_info.value)
