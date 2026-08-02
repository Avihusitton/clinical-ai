# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from durable_chunk_reconstruction import (
    _direct_identifier_findings,
    _queue_by_chunk,
)


class DurableChunkReconstructionTests(unittest.TestCase):
    def test_queue_groups_only_valid_chunk_ids(self) -> None:
        grouped = _queue_by_chunk(
            [
                {"chunk_id": "a" * 24},
                {"chunk_id": "a" * 24},
                {"chunk_id": "not-valid"},
            ]
        )
        self.assertEqual(set(grouped), {"a" * 24})
        self.assertEqual(len(grouped["a" * 24]), 2)

    def test_direct_identifier_screen(self) -> None:
        findings = _direct_identifier_findings(
            "טלפון 050-1234567 ודוא״ל person@example.com"
        )
        self.assertEqual(findings, ["email", "phone"])

    def test_clean_educational_text_passes_direct_screen(self) -> None:
        self.assertEqual(
            _direct_identifier_findings(
                "דוגמה לימודית כללית ללא פרטים מזהים"
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
