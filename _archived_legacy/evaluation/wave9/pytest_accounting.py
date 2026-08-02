# -*- coding: utf-8 -*-
"""
evaluation/wave9/pytest_accounting.py
Parses WAVE_9_4R_FINAL_JUNIT.xml and produces a JSON accounting summary.
"""

import json
import os
import sys
import xml.etree.ElementTree as ET


def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    junit_path = os.path.join(project_root, "tests", "WAVE_9_4R_FINAL_JUNIT.xml")
    output_path = os.path.join(project_root, "tests", "WAVE_9_4R_PYTEST_ACCOUNTING.json")

    if not os.path.exists(junit_path):
        result = {
            "error": "WAVE_9_4R_FINAL_JUNIT.xml not found",
            "tests_collected": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "test_errors": 0,
            "tests_skipped": 0,
            "tests_unaccounted": 0,
            "accounting_exit_code": 2
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result, indent=2))
        sys.exit(2)

    try:
        tree = ET.parse(junit_path)
        root = tree.getroot()
    except Exception as e:
        result = {
            "error": f"Failed to parse JUnit XML: {e}",
            "tests_collected": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "test_errors": 0,
            "tests_skipped": 0,
            "tests_unaccounted": 0,
            "accounting_exit_code": 2
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result, indent=2))
        sys.exit(2)

    # Parse testsuite attributes
    tests_collected = 0
    tests_failed = 0
    test_errors = 0
    tests_skipped = 0

    for testsuite in root.iter("testsuite"):
        tests_collected += int(testsuite.get("tests", 0))
        tests_failed += int(testsuite.get("failures", 0))
        test_errors += int(testsuite.get("errors", 0))
        tests_skipped += int(testsuite.get("skipped", 0))

    tests_passed = tests_collected - tests_failed - test_errors - tests_skipped
    tests_unaccounted = tests_collected - (tests_passed + tests_failed + test_errors + tests_skipped)

    # Collect failed test names
    failed_tests = []
    error_tests = []
    for testcase in root.iter("testcase"):
        for failure in testcase.iter("failure"):
            failed_tests.append(f"{testcase.get('classname', '')}::{testcase.get('name', '')}")
        for error in testcase.iter("error"):
            error_tests.append(f"{testcase.get('classname', '')}::{testcase.get('name', '')}")

    result = {
        "tests_collected": tests_collected,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "test_errors": test_errors,
        "tests_skipped": tests_skipped,
        "tests_unaccounted": tests_unaccounted,
        "failed_tests": failed_tests,
        "error_tests": error_tests,
        "accounting_exit_code": 0
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
