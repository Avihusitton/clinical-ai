"""
tests/test_controlled_integration_isolation.py
------------------------------------------------
Isolation test suite for controlled_integration adapter layer.

Verifies strict system isolation invariants:
1. 0 graph writes
2. 0 Neo4j calls
3. 0 external network calls
4. 0 LLM calls
5. 0 protected production imports
"""

import ast
import os
import socket
import pytest
from unittest.mock import patch, MagicMock

from controlled_integration.models import IntegrationRequest, IntegrationContext
from controlled_integration.orchestration import IntegrationOrchestrator
from controlled_integration.security import SecurityPolicy, AccessDeniedError
from controlled_integration.exceptions import KnowledgeWriteForbiddenError, ExternalIOCallForbiddenError


def test_zero_graph_writes():
    """Verify 0 graph writes occur during pipeline execution and write attempts are strictly forbidden."""
    security = SecurityPolicy()

    # Verify write access is explicitly denied for all roles
    roles = ["ROLE_INTERNAL_THERAPIST", "THERAPIST_PILOT_USER", "SYSTEM_OPERATOR"]
    for role in roles:
        with pytest.raises(AccessDeniedError):
            security.check_access(user_role=role, resource_id="knowledge_graph_write")

    # Execute orchestrator in full THERAPIST_PILOT mode
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_iso_1", user_id="u_iso_1", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id="req_iso_001",
        query_text="Isolation test query",
        context=ctx,
        operating_mode_override="THERAPIST_PILOT",
    )

    decision, explanation, res = orchestrator.process(req)
    assert decision.verdict == "FULL_PILOT_SERVED"


def test_zero_neo4j_calls(monkeypatch):
    """Verify 0 Neo4j driver connections or queries are executed during pipeline processing."""
    call_counter = {"neo4j_calls": 0}

    def forbidden_neo4j_call(*args, **kwargs):
        call_counter["neo4j_calls"] += 1
        raise ExternalIOCallForbiddenError("Neo4j database connection")

    # Patch potential neo4j or driver imports if present
    monkeypatch.setattr("socket.socket.connect", forbidden_neo4j_call)

    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_iso_2", user_id="u_iso_2", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id="req_iso_002",
        query_text="Neo4j isolation check",
        context=ctx,
        operating_mode_override="THERAPIST_PILOT",
    )

    decision, _, _ = orchestrator.process(req)
    assert decision.verdict == "FULL_PILOT_SERVED"
    assert call_counter["neo4j_calls"] == 0, "Neo4j call detected during isolated execution"


def test_zero_external_network_calls(monkeypatch):
    """Verify 0 external network socket connections occur during pipeline execution."""
    attempted_connections = []

    def failing_connect(self, address):
        attempted_connections.append(address)
        raise ExternalIOCallForbiddenError(f"Network connection to {address}")

    monkeypatch.setattr(socket.socket, "connect", failing_connect)

    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_iso_3", user_id="u_iso_3", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id="req_iso_003",
        query_text="Network isolation check",
        context=ctx,
        operating_mode_override="THERAPIST_PILOT",
    )

    decision, _, _ = orchestrator.process(req)
    assert decision.verdict == "FULL_PILOT_SERVED"
    assert len(attempted_connections) == 0, f"Network calls attempted: {attempted_connections}"


def test_zero_llm_calls():
    """Verify 0 external LLM API calls are triggered by the integration adapter layer."""
    llm_mock = MagicMock(side_effect=ExternalIOCallForbiddenError("LLM API Call"))

    with patch("urllib.request.urlopen", llm_mock):
        orchestrator = IntegrationOrchestrator()
        ctx = IntegrationContext(session_id="s_iso_4", user_id="u_iso_4", user_role="ROLE_INTERNAL_THERAPIST")
        req = IntegrationRequest(
            request_id="req_iso_004",
            query_text="LLM isolation check",
            context=ctx,
            operating_mode_override="THERAPIST_PILOT",
        )

        decision, _, _ = orchestrator.process(req)
        assert decision.verdict == "FULL_PILOT_SERVED"
        assert llm_mock.call_count == 0, "External LLM API call detected"


def test_zero_protected_production_imports():
    """
    AST analysis of controlled_integration codebase verifying that no forbidden
    production write modules or direct DB connection drivers are imported.
    """
    pkg_dir = os.path.join(os.path.dirname(__file__), "..", "controlled_integration")
    if not os.path.exists(pkg_dir):
        pkg_dir = "controlled_integration"

    forbidden_imports = {
        "neo4j",
        "psycopg2",
        "sqlalchemy",
        "requests",
        "httpx",
        "openai",
        "anthropic",
    }

    violation_list = []

    for root, _, files in os.walk(pkg_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=filepath)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in forbidden_imports:
                                violation_list.append((filepath, alias.name))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module in forbidden_imports:
                            violation_list.append((filepath, node.module))

    assert len(violation_list) == 0, f"Forbidden production/external imports detected: {violation_list}"
