import os
import argparse
from neo4j import GraphDatabase
from config import Config

def clean_shadow_nodes(driver, pilot_id: str):
    print(f"Cleaning up shadow nodes for pilot ID: {pilot_id}...")
    
    with driver.session() as session:
        # Delete OfficialEntryShadow nodes
        res1 = session.run("""
        MATCH (n:OfficialEntryShadow {pilot_id: $pilot_id})
        DETACH DELETE n
        RETURN count(n) as deleted_count
        """, pilot_id=pilot_id).single()
        print(f"Deleted {res1['deleted_count']} OfficialEntryShadow nodes.")
        
        # Delete OfficialAliasShadow nodes
        res2 = session.run("""
        MATCH (n:OfficialAliasShadow {pilot_id: $pilot_id})
        DETACH DELETE n
        RETURN count(n) as deleted_count
        """, pilot_id=pilot_id).single()
        print(f"Deleted {res2['deleted_count']} OfficialAliasShadow nodes.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up pilot/shadow nodes from Neo4j.")
    parser.add_argument("--pilot_id", type=str, required=True, help="The pilot ID to clean up.")
    args = parser.parse_args()
    
    cfg = Config()
    driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))
    try:
        clean_shadow_nodes(driver, args.pilot_id)
    finally:
        driver.close()
