import os
import sys
import uuid
import json
from dotenv import load_dotenv

# Ensure root directory is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from official_glossary_loader import OfficialGlossaryLoader
from official_glossary_store import OfficialGlossaryStore
from neo4j import GraphDatabase

def main():
    load_dotenv()
    
    allow_pilot = os.environ.get('ALLOW_GATE_A_SHADOW_PILOT', 'false').lower() == 'true'
    environment = os.environ.get('NEO4J_ENVIRONMENT', '')
    configured_test_db = os.environ.get('NEO4J_TEST_DATABASE', '')
    gate_a_final_signoff = os.environ.get('GATE_A_FINAL_SIGNOFF', 'false').lower() == 'true'
    
    if gate_a_final_signoff:
        assert environment == "test", "NEO4J_ENVIRONMENT must be 'test' when GATE_A_FINAL_SIGNOFF is true"
        assert allow_pilot is True, "ALLOW_GATE_A_SHADOW_PILOT must be true when GATE_A_FINAL_SIGNOFF is true"
        assert configured_test_db != "", "NEO4J_TEST_DATABASE must not be empty when GATE_A_FINAL_SIGNOFF is true"
    else:
        if not allow_pilot and environment != "test":
            print("SKIPPED: Real Shadow Pilot is not allowed by configuration")
            sys.exit(77)
            
    cfg = Config()
    
    # Static guard against unrestricted cleanup
    runner_file = __file__
    with open(runner_file, 'r', encoding='utf-8') as f:
        src = f.read()
    assert 'MATCH (n {pilot_id: ' + '$pid}) DETACH DELETE n' not in src
    
    original_error = None
    cleanup_error = None
    test_succeeded = False
    
    pilot_id = f"GATE_A_REAL_SHADOW_{uuid.uuid4().hex[:8].upper()}"
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
            
    driver = None
    try:
        driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))
        
        with driver.session() as s:
            db_info = s.run("CALL db.info() YIELD name").single()
            actual_database_name = db_info["name"] if db_info else "unknown"
            
            labels_query = '''
            MATCH (n)
            UNWIND labels(n) AS label
            RETURN label, count(*) AS count
            ORDER BY label
            '''
            rels_query = '''
            MATCH ()-[r]->()
            RETURN type(r) AS relationship_type, count(*) AS count
            ORDER BY relationship_type
            '''
            prod_labels_before = {r["label"]: r["count"] for r in s.run(labels_query).data()}
            prod_rels_before = {r["relationship_type"]: r["count"] for r in s.run(rels_query).data()}
            
        if gate_a_final_signoff:
            assert configured_test_db == actual_database_name
            
        database_identity_verified = (
            environment == "test"
            and allow_pilot is True
            and configured_test_db == actual_database_name
        )
        database_is_not_production = database_identity_verified
        
        store = OfficialGlossaryStore("tests/shadow_pilot_fixture.jsonl")
        store.load()
        fixture_card_count = len(store.entries)
        loader = OfficialGlossaryLoader(store, driver)
        
        original_session_func = driver.session
        def hooked_session(*args, **kwargs):
            return QueryInterceptor(original_session_func(*args, **kwargs))
            
        driver.session = hooked_session
        loader.dry_run(pilot_id)
        driver.session = original_session_func
        
        write_verbs = ["CREATE", "MERGE", "SET", "DELETE", "DETACH", "REMOVE", "DROP"]
        dry_run_write_query_count = sum(1 for q in queries_executed if any(v in q.upper() for v in write_verbs))
        dry_run_read_query_count = len(queries_executed) - dry_run_write_query_count
        
        loader.load_shadow(pilot_id)
        
        with driver.session() as s:
            shadow_entries_after_load = s.run("MATCH (n:OfficialEntryShadow {pilot_id: $pid}) RETURN count(n) as c", pid=pilot_id).single()["c"]
            shadow_aliases_after_load = s.run("MATCH (n:OfficialAliasShadow {pilot_id: $pid}) RETURN count(n) as c", pid=pilot_id).single()["c"]
            shadow_alias_of_after_load = s.run("MATCH (:OfficialAliasShadow {pilot_id: $pid})-[r:ALIAS_OF]->(:OfficialEntryShadow {pilot_id: $pid}) RETURN count(r) as c", pid=pilot_id).single()["c"]
            
            cross_boundary_query = '''
            MATCH (s)
            WHERE (s:OfficialEntryShadow OR s:OfficialAliasShadow)
              AND s.pilot_id = $pilot_id
            MATCH (s)-[r]-(p)
            WHERE NOT p:OfficialEntryShadow
              AND NOT p:OfficialAliasShadow
            RETURN count(*) AS cross_boundary_relationships
            '''
            cross_boundary_relationships = s.run(cross_boundary_query, pilot_id=pilot_id).single()["cross_boundary_relationships"]
            orphan_shadow_aliases = s.run("MATCH (a:OfficialAliasShadow {pilot_id: $pid}) WHERE NOT (a)-[:ALIAS_OF]->(:OfficialEntryShadow) RETURN count(a) as c", pid=pilot_id).single()["c"]
            shadow_entries_missing_pilot_id = s.run("MATCH (e:OfficialEntryShadow) WHERE e.pilot_id IS NULL RETURN count(e) as c").single()["c"]
            shadow_aliases_missing_pilot_id = s.run("MATCH (a:OfficialAliasShadow) WHERE a.pilot_id IS NULL RETURN count(a) as c").single()["c"]
            shadow_aliases_linked_to_wrong_pilot = s.run("MATCH (a:OfficialAliasShadow {pilot_id: $pid})-[:ALIAS_OF]->(e:OfficialEntryShadow) WHERE a.pilot_id <> e.pilot_id RETURN count(a) as c", pid=pilot_id).single()["c"]
            
        dry2 = loader.dry_run(pilot_id)
        second_load_new_entries = dry2.get("new_entries", 0)
        second_load_updated_entries = dry2.get("updated_entries", 0)
        second_load_unchanged_entries = dry2.get("unchanged_entries", 0)
        loader.load_shadow(pilot_id)
        
        assert fixture_card_count == 3
        assert dry_run_write_query_count == 0
        assert shadow_entries_after_load == 3
        assert shadow_aliases_after_load > 0
        assert shadow_alias_of_after_load > 0
        assert cross_boundary_relationships == 0
        assert orphan_shadow_aliases == 0
        assert shadow_entries_missing_pilot_id == 0
        assert shadow_aliases_missing_pilot_id == 0
        assert shadow_aliases_linked_to_wrong_pilot == 0
        assert second_load_new_entries == 0
        assert second_load_updated_entries == 0
        assert second_load_unchanged_entries == 3
        
        test_succeeded = True
        
    except Exception as exc:
        original_error = exc
    finally:
        try:
            if driver:
                with driver.session() as s:
                    non_shadow_nodes_with_pilot_id = s.run('''
                    MATCH (n {pilot_id: $pid})
                    WHERE NOT n:OfficialEntryShadow
                      AND NOT n:OfficialAliasShadow
                    RETURN count(n) AS c
                    ''', pid=pilot_id).single()["c"]
                    
                    assert non_shadow_nodes_with_pilot_id == 0
                    
                    s.run('''
                    MATCH (n)
                    WHERE (n:OfficialEntryShadow OR n:OfficialAliasShadow)
                      AND n.pilot_id = $pid
                    DETACH DELETE n
                    ''', pid=pilot_id)
                    
                with driver.session() as s:
                    shadow_entries_after_cleanup = s.run("MATCH (n:OfficialEntryShadow {pilot_id: $pid}) RETURN count(n) as c", pid=pilot_id).single()["c"]
                    shadow_aliases_after_cleanup = s.run("MATCH (n:OfficialAliasShadow {pilot_id: $pid}) RETURN count(n) as c", pid=pilot_id).single()["c"]
                    
                    prod_labels_after = {r["label"]: r["count"] for r in s.run(labels_query).data()}
                    prod_rels_after = {r["relationship_type"]: r["count"] for r in s.run(rels_query).data()}
                    
                assert shadow_entries_after_cleanup == 0
                assert shadow_aliases_after_cleanup == 0
                assert prod_labels_before == prod_labels_after
                assert prod_rels_before == prod_rels_after
                
                if original_error is None and test_succeeded:
                    report = {
                        "backend_type": "DEDICATED_NEO4J_TEST_DATABASE",
                        "environment_marker": environment,
                        "database_name": actual_database_name,
                        "configured_test_database": configured_test_db,
                        "database_identity_verified": database_identity_verified,
                        "database_is_not_production": database_is_not_production,
                        "pilot_id": pilot_id,
                        "fixture_card_count": fixture_card_count,
                        "dry_run_read_query_count": dry_run_read_query_count,
                        "dry_run_write_query_count": dry_run_write_query_count,
                        "shadow_entries_after_load": shadow_entries_after_load,
                        "shadow_aliases_after_load": shadow_aliases_after_load,
                        "shadow_alias_of_after_load": shadow_alias_of_after_load,
                        "cross_boundary_relationships": cross_boundary_relationships,
                        "orphan_shadow_aliases": orphan_shadow_aliases,
                        "shadow_entries_missing_pilot_id": shadow_entries_missing_pilot_id,
                        "shadow_aliases_missing_pilot_id": shadow_aliases_missing_pilot_id,
                        "shadow_aliases_linked_to_wrong_pilot": shadow_aliases_linked_to_wrong_pilot,
                        "second_load_new_entries": second_load_new_entries,
                        "second_load_updated_entries": second_load_updated_entries,
                        "second_load_unchanged_entries": second_load_unchanged_entries,
                        "shadow_entries_after_cleanup": shadow_entries_after_cleanup,
                        "shadow_aliases_after_cleanup": shadow_aliases_after_cleanup,
                        "non_shadow_nodes_with_pilot_id": non_shadow_nodes_with_pilot_id,
                        "production_counts_before_by_label": prod_labels_before,
                        "production_counts_after_by_label": prod_labels_after,
                        "production_relationships_before_by_type": prod_rels_before,
                        "production_relationships_after_by_type": prod_rels_after
                    }
                    with open("tests/REAL_SHADOW_PILOT_REPORT.json", "w", encoding="utf-8") as f:
                        json.dump(report, f, indent=2)
                        
        except Exception as exc:
            cleanup_error = exc
        finally:
            if driver:
                driver.close()
                
    if original_error is not None:
        raise original_error

    if cleanup_error is not None:
        raise cleanup_error

    assert test_succeeded is True
    print("SUCCESS: Real Shadow Pilot completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    main()
