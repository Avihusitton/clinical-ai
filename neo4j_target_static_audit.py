# -*- coding: utf-8 -*-
"""Classify Neo4j target configuration without exposing secrets or connecting."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Mapping


NONPRODUCTION_PATTERN = re.compile(
    r"(?:staging|stage|development|dev|test|sandbox|localhost|127\.0\.0\.1)",
    re.IGNORECASE,
)
PRODUCTION_PATTERN = re.compile(
    r"(?:^|[._:/-])(?:production|prod)(?:$|[._:/-])",
    re.IGNORECASE,
)


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or "=" not in stripped
        ):
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def audit_target_values(values: Mapping[str, str]) -> dict:
    """Return only configuration classifications and presence booleans."""
    uri = str(values.get("NEO4J_URI", ""))
    database = str(values.get("NEO4J_DATABASE", ""))
    environment = str(values.get("NEO4J_ENVIRONMENT", ""))
    user = str(
        values.get("NEO4J_USER")
        or values.get("NEO4J_USERNAME")
        or ""
    )
    password = str(values.get("NEO4J_PASSWORD", ""))

    combined_identity = "|".join([uri, database, environment])
    forbidden_production_marker = bool(
        PRODUCTION_PATTERN.search(combined_identity)
    )
    uri_nonproduction = bool(NONPRODUCTION_PATTERN.search(uri))
    database_nonproduction = bool(
        NONPRODUCTION_PATTERN.search(database)
    )
    environment_nonproduction = bool(
        NONPRODUCTION_PATTERN.search(environment)
    )
    nonproduction_marker = (
        uri_nonproduction
        or database_nonproduction
        or environment_nonproduction
    )
    blockers: list[str] = []
    if not uri:
        blockers.append("NEO4J_URI_MISSING")
    if not user:
        blockers.append("NEO4J_USER_MISSING")
    if not password:
        blockers.append("NEO4J_PASSWORD_MISSING")
    if forbidden_production_marker:
        blockers.append("PRODUCTION_MARKER_FORBIDDEN")
    if not nonproduction_marker:
        blockers.append("NONPRODUCTION_MARKER_REQUIRED")

    ready = not blockers
    return {
        "schema_version": "0.1",
        "status": (
            "PASS_STATIC_CONFIG_READY_FOR_READONLY_TARGET_VERIFICATION"
            if ready
            else "BLOCKED_STATIC_TARGET_CONFIG"
        ),
        "configuration": {
            "uri_configured": bool(uri),
            "database_configured": bool(database),
            "user_configured": bool(user),
            "password_configured": bool(password),
            "environment_configured": bool(environment),
            "uri_has_nonproduction_marker": uri_nonproduction,
            "database_has_nonproduction_marker": (
                database_nonproduction
            ),
            "environment_has_nonproduction_marker": (
                environment_nonproduction
            ),
            "forbidden_production_marker": (
                forbidden_production_marker
            ),
        },
        "target_classification": (
            "EXPLICIT_NONPRODUCTION_CONFIGURATION"
            if ready
            else "UNRESOLVED"
        ),
        "runtime_readonly_verification": "NOT_RUN",
        "blockers": blockers,
        "secrets_emitted": False,
        "neo4j_connections": 0,
        "neo4j_reads": 0,
        "neo4j_writes": 0,
        "eligible_for_readonly_runtime_verification": ready,
        "eligible_for_staging_write": False,
        "eligible_for_production_execution": False,
    }


def audit_env_file(path: Path, output_path: Path) -> dict:
    report = audit_target_values(_read_env(Path(path).resolve()))
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = audit_env_file(args.env_file, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
