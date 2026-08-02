# -*- coding: utf-8 -*-
from shadow_wiring.redaction import RedactionEngine


def test_israeli_pii_detection():
    # Israeli ID (9 digits)
    has_pii, redacted, tokens = RedactionEngine.scan_and_redact("Patient ID 123456789 presented with anxiety.")
    assert has_pii is True
    assert "123456789" in tokens

    # Israeli Phone number (050)
    has_pii, redacted, tokens = RedactionEngine.scan_and_redact("Call 050-1234567 for follow up.")
    assert has_pii is True
    assert "050-1234567" in tokens

    # Email address
    has_pii, redacted, tokens = RedactionEngine.scan_and_redact("Contact patient at test@example.com.")
    assert has_pii is True

    # HMO ID
    has_pii, redacted, tokens = RedactionEngine.scan_and_redact("Ref: Clalit-ID-998877")
    assert has_pii is True


def test_clean_text_no_pii():
    has_pii, redacted, tokens = RedactionEngine.scan_and_redact("מהם העקרונות של טיפול בהחפצה ומיינדפולנס ב-ACT?")
    assert has_pii is False
    assert len(tokens) == 0


def test_user_id_hashing():
    h1 = RedactionEngine.hash_user_id("user_123")
    h2 = RedactionEngine.hash_user_id("user_123")
    h3 = RedactionEngine.hash_user_id("user_456")

    assert h1.startswith("sha256:")
    assert h1 == h2
    assert h1 != h3


def test_redaction_negative_clean_cases():
    import json
    neg_path = "tests/fixtures/shadow_wiring/redaction_negative_cases.jsonl"
    with open(neg_path, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    assert len(cases) >= 60
    for c in cases:
        has_pii, _, _ = RedactionEngine.scan_and_redact(c["query_text"])
        assert has_pii is False, f"Unexpected PII block in case {c['case_id']}: {c['query_text']}"
