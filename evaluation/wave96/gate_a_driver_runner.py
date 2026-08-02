import sys
import os
import json
import argparse

# Ensure project root is in sys.path when executed as a standalone script
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import Config
from official_glossary_loader import OfficialGlossaryLoader
from official_glossary_store import OfficialGlossaryStore

def run_dry_run_no_writes():
    from neo4j import GraphDatabase
    cfg = Config()
    
    queries_executed = []
    
    class QueryInterceptor:
        def __init__(self, original_session):
            self.original_session = original_session

        def __enter__(self):
            self.original_session.__enter__()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            return self.original_session.__exit__(exc_type, exc_val, exc_tb)
            
        def run(self, query, **kwargs):
            queries_executed.append(query)
            return self.original_session.run(query, **kwargs)
            
        def __getattr__(self, name):
            return getattr(self.original_session, name)

    driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))
    store = OfficialGlossaryStore("data/official_glossary/glossary.json")
    loader = OfficialGlossaryLoader(store, driver)
    
    original_session_func = driver.session
    
    def hooked_session(*args, **kwargs):
        sess = original_session_func(*args, **kwargs)
        return QueryInterceptor(sess)

    driver.session = hooked_session
    
    result = loader.dry_run("PILOT_GATE_A_TEST")
    
    write_verbs = ["CREATE", "MERGE", "SET", "DELETE", "DETACH", "REMOVE", "DROP"]
    
    write_queries_detected = []
    read_query_count = 0
    write_query_count = 0
    
    for q in queries_executed:
        is_write = any(verb in q.upper() for verb in write_verbs)
        if is_write:
            write_query_count += 1
            write_queries_detected.append(q)
        else:
            read_query_count += 1
            
    assert write_query_count == 0, f"Found write queries: {write_queries_detected}"
    
    required_keys = [
        "new_entries", "updated_entries", "unchanged_entries", "duplicate_card_ids",
        "alias_collisions", "unresolved_targets", "self_links", "invalid_types", "invalid_certainty",
        "exact_legacy_concept_mappings", "alias_legacy_concept_mappings", 
        "exact_legacy_exercise_mappings", "ambiguous_legacy_mappings", "unmapped_official_entries"
    ]

    for k in required_keys:
        assert k in result, f"Missing key in dry_run result: {k}"

    report = {
        "read_query_count": read_query_count,
        "write_query_count": write_query_count,
        "write_queries_detected": write_queries_detected
    }
    
    with open("tests/DRY_RUN_REPORT.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

def run_shadow_isolation():
    from neo4j import GraphDatabase
    cfg = Config()
    driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))
    store = OfficialGlossaryStore("tests/shadow_pilot_fixture.jsonl")
    store.load()
    loader = OfficialGlossaryLoader(store, driver)
    
    pilot_id = "SHADOW_PILOT_TEST"
    
    try:
        with driver.session() as s:
            prod_labels_before = {r["label"]: r["count"] for r in s.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count").data()}
            prod_rels_before = {r["type"]: r["count"] for r in s.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count").data()}
            
        dry1 = loader.dry_run(pilot_id)
        loader.load_shadow(pilot_id)
        
        with driver.session() as s:
            shadow_entries_after_load = s.run("MATCH (n:OfficialEntryShadow {pilot_id: $pid}) RETURN count(n) as c", pid=pilot_id).single()["c"]
            shadow_aliases_after_load = s.run("MATCH (n:OfficialAliasShadow {pilot_id: $pid}) RETURN count(n) as c", pid=pilot_id).single()["c"]
            shadow_alias_of_after_load = s.run("MATCH (:OfficialAliasShadow {pilot_id: $pid})-[r:ALIAS_OF]->(:OfficialEntryShadow {pilot_id: $pid}) RETURN count(r) as c", pid=pilot_id).single()["c"]
            
            cross_boundary_query = """
MATCH (s)
WHERE (s:OfficialEntryShadow OR s:OfficialAliasShadow)
  AND s.pilot_id = $pilot_id
MATCH (s)-[r]-(p)
WHERE NOT p:OfficialEntryShadow
  AND NOT p:OfficialAliasShadow
RETURN count(*) AS cross_boundary_relationships
"""
            cross_boundary = s.run(cross_boundary_query, pilot_id=pilot_id).single()["cross_boundary_relationships"]
            orphan_aliases = s.run("MATCH (a:OfficialAliasShadow {pilot_id: $pid}) WHERE NOT (a)-[:ALIAS_OF]->(:OfficialEntryShadow) RETURN count(a) as c", pid=pilot_id).single()["c"]
            entries_no_pilot = s.run("MATCH (e:OfficialEntryShadow) WHERE e.pilot_id IS NULL RETURN count(e) as c").single()["c"]
            aliases_no_pilot = s.run("MATCH (a:OfficialAliasShadow) WHERE a.pilot_id IS NULL RETURN count(a) as c").single()["c"]
            aliases_wrong_pilot = s.run("MATCH (a:OfficialAliasShadow {pilot_id: $pid})-[:ALIAS_OF]->(e:OfficialEntryShadow) WHERE a.pilot_id <> e.pilot_id RETURN count(a) as c", pid=pilot_id).single()["c"]
            
        dry2 = loader.dry_run(pilot_id)
        second_load_new_entries = dry2.get("new_entries", 0)
        second_load_updated_entries = dry2.get("updated_entries", 0)
        second_load_unchanged_entries = dry2.get("unchanged_entries", 0)
        loader.load_shadow(pilot_id)
        
        assert shadow_entries_after_load == 3
        assert shadow_aliases_after_load > 0
        assert shadow_alias_of_after_load > 0
        assert cross_boundary == 0
        assert orphan_aliases == 0
        assert entries_no_pilot == 0
        assert aliases_no_pilot == 0
        assert aliases_wrong_pilot == 0
        assert second_load_new_entries == 0
        assert second_load_updated_entries == 0
        assert second_load_unchanged_entries == 3
    finally:
        with driver.session() as s:
            s.run("MATCH (n {pilot_id: $pid}) DETACH DELETE n", pid=pilot_id)
    
    with driver.session() as s:
        shadow_entries_after_cleanup = s.run("MATCH (n:OfficialEntryShadow {pilot_id: $pid}) RETURN count(n) as c", pid=pilot_id).single()["c"]
        shadow_aliases_after_cleanup = s.run("MATCH (n:OfficialAliasShadow {pilot_id: $pid}) RETURN count(n) as c", pid=pilot_id).single()["c"]
        
        prod_labels_after = {r["label"]: r["count"] for r in s.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count").data()}
        prod_rels_after = {r["type"]: r["count"] for r in s.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count").data()}
        
    assert shadow_entries_after_cleanup == 0
    assert shadow_aliases_after_cleanup == 0
    
    assert prod_labels_before == prod_labels_after
    assert prod_rels_before == prod_rels_after

    report = {
        "pilot_id": pilot_id,
        "shadow_entries_after_load": shadow_entries_after_load,
        "shadow_aliases_after_load": shadow_aliases_after_load,
        "shadow_alias_of_after_load": shadow_alias_of_after_load,
        "cross_boundary_relationships": cross_boundary,
        "orphan_shadow_aliases": orphan_aliases,
        "shadow_entries_missing_pilot_id": entries_no_pilot,
        "shadow_aliases_missing_pilot_id": aliases_no_pilot,
        "shadow_aliases_linked_to_wrong_pilot": aliases_wrong_pilot,
        "second_load_new_entries": second_load_new_entries,
        "second_load_updated_entries": second_load_updated_entries,
        "second_load_unchanged_entries": second_load_unchanged_entries,
        "shadow_entries_after_cleanup": shadow_entries_after_cleanup,
        "shadow_aliases_after_cleanup": shadow_aliases_after_cleanup,
        "production_counts_before_by_label": prod_labels_before,
        "production_counts_after_by_label": prod_labels_after,
        "production_relationships_before_by_type": prod_rels_before,
        "production_relationships_after_by_type": prod_rels_after
    }
    
    with open("tests/ISOLATION_REPORT.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Gate A Driver Runner")
    parser.add_argument("--test", choices=["test_dry_run_no_writes", "test_shadow_isolation", "all"], default="all")
    args = parser.parse_args()

    try:
        if args.test in ["test_dry_run_no_writes", "all"]:
            run_dry_run_no_writes()
        if args.test in ["test_shadow_isolation", "all"]:
            run_shadow_isolation()
        sys.exit(0)
    except Exception as e:
        exc_type = type(e).__name__
        try:
            from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError, DriverError
            is_skip_exc = isinstance(e, (ServiceUnavailable, AuthError, Neo4jError, DriverError)) or exc_type in ["ServiceUnavailable", "AuthError", "Neo4jError", "DriverError"]
        except ImportError:
            is_skip_exc = False

        if is_skip_exc or isinstance(e, ConnectionRefusedError):
            sys.stderr.write(f"Database skip condition encountered: {exc_type}\n")
            sys.exit(77)
        
        sys.stderr.write(f"Gate A runner failure: {exc_type}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
