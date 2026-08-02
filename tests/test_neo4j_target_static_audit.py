# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import unittest

from neo4j_target_static_audit import audit_target_values


class Neo4jTargetStaticAuditTests(unittest.TestCase):
    def test_localhost_configuration_is_nonproduction(self) -> None:
        report = audit_target_values(
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "top-secret",
            }
        )
        self.assertEqual(
            report["status"],
            "PASS_STATIC_CONFIG_READY_FOR_READONLY_TARGET_VERIFICATION",
        )
        self.assertTrue(
            report["eligible_for_readonly_runtime_verification"]
        )
        self.assertEqual(report["neo4j_connections"], 0)
        self.assertNotIn("top-secret", json.dumps(report))

    def test_production_marker_is_blocked(self) -> None:
        report = audit_target_values(
            {
                "NEO4J_URI": "neo4j+s://production.example",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "secret",
            }
        )
        self.assertEqual(
            report["status"],
            "BLOCKED_STATIC_TARGET_CONFIG",
        )
        self.assertIn(
            "PRODUCTION_MARKER_FORBIDDEN",
            report["blockers"],
        )
        self.assertFalse(report["eligible_for_staging_write"])

    def test_unmarked_remote_target_is_blocked(self) -> None:
        report = audit_target_values(
            {
                "NEO4J_URI": "neo4j+s://graph.example",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "secret",
            }
        )
        self.assertIn(
            "NONPRODUCTION_MARKER_REQUIRED",
            report["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
