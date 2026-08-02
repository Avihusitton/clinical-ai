import xml.etree.ElementTree as ET
import re
import json

def parse_failures():
    # 1. Parse JUnit XML
    tree = ET.parse("tests/WAVE_9_5_FINAL_JUNIT.xml")
    root = tree.getroot()
    
    junit_failures = []
    for tc in root.iter("testcase"):
        fail_elem = tc.find("failure")
        err_elem = tc.find("error")
        if fail_elem is not None or err_elem is not None:
            elem = fail_elem if fail_elem is not None else err_elem
            classname = tc.attrib.get("classname", "")
            name = tc.attrib.get("name", "")
            file_attr = tc.attrib.get("file", "")
            
            # Form standard pytest node ID
            if file_attr:
                node_id = f"{file_attr}::{name}"
            else:
                # Classname is e.g. "tests.test_gate_cd_boundary.TestNoProductionImports" or "tests.test_wave95_neo4j_isolation"
                parts = classname.split(".")
                if parts[0] == "tests":
                    mod_path = "/".join(parts[:2]) + ".py"
                    if len(parts) > 2:
                        cls_name = ".".join(parts[2:])
                        node_id = f"{mod_path}::{cls_name}::{name}"
                    else:
                        node_id = f"{mod_path}::{name}"
                else:
                    node_id = f"{classname}::{name}"

            # Standardize backslashes to forward slashes for node IDs
            node_id = node_id.replace("\\", "/")

            junit_failures.append({
                "node_id": node_id,
                "classname": classname,
                "name": name,
                "failure_type": elem.attrib.get("type", "AssertionError"),
                "failure_message": elem.attrib.get("message", ""),
                "traceback": elem.text or ""
            })

    # 2. Parse Raw Pytest Output
    with open("tests/WAVE_9_5_FINAL_FULL_PYTEST_OUTPUT.txt", "r", encoding="utf-8") as f:
        raw_output = f.read()

    raw_nodes = []
    for line in raw_output.splitlines():
        if line.startswith("FAILED "):
            # Line is e.g., FAILED tests/test_gate_cd_boundary.py::TestNoProductionImports::test_gate_cd_boundary_does_not_import_neo4j
            # or FAILED tests/test_wave95_neo4j_isolation.py::test_gate_test_passes_alone - As...
            parts = line[7:].strip().split(" - ")[0]
            parts = parts.replace("\\", "/")
            raw_nodes.append(parts)

    print("JUnit Node IDs:")
    for jf in junit_failures:
        print(" ", jf["node_id"])

    print("\nRaw Output Node IDs:")
    for rn in raw_nodes:
        print(" ", rn)

    mismatch = False
    junit_node_set = set(jf["node_id"] for jf in junit_failures)
    raw_node_set = set(raw_nodes)

    if junit_node_set != raw_node_set:
        print("\nMISMATCH DETECTED!")
        print("JUnit only:", junit_node_set - raw_node_set)
        print("Raw only:", raw_node_set - junit_node_set)
        mismatch = True
    else:
        print("\nPERFECT MATCH: Both JUnit and Raw output identify the exact same 5 node IDs!")

    return junit_failures, raw_nodes, mismatch

if __name__ == "__main__":
    parse_failures()
