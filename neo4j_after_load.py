from config import Config
from neo4j import GraphDatabase

cfg = Config()
driver = GraphDatabase.driver(
    cfg.neo4j_uri,
    auth=(cfg.neo4j_user, cfg.neo4j_password),
)

try:
    with driver.session() as s:
        row = s.run("""
            MATCH (n)
            OPTIONAL MATCH ()-[r]->()
            RETURN
              count(DISTINCT n) AS nodes,
              count(r) AS relationships,
              count { (:Chunk) } AS chunks,
              count { ()-[:HAS_CANDIDATE]->() } AS candidates,
              count { ()-[:LINKED_TO]->() } AS linked,
              count { ()-[:WORKS_ON]->() } AS works_on,
              count { ()-[x:LEADS_TO|IS_SYMPTOM_OF|PREVENTS|IS_RECOMMENDED_FOR|IS_CONTRAINDICATED_FOR]->() } AS concept_relationships
        """).single()

    for key in (
        "nodes", "relationships", "chunks", "candidates",
        "linked", "works_on", "concept_relationships",
    ):
        print(f"{key}: {row[key]}")
finally:
    driver.close()
