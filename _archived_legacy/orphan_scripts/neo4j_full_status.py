from config import Config
from neo4j import GraphDatabase

cfg = Config()
driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))

try:
    with driver.session() as s:
        row = s.run("""
            MATCH (n)
            RETURN
              count(DISTINCT n) AS nodes,
              count { (:Chunk) } AS chunks,
              count { (:Concept) } AS concepts,
              count { (:Exercise) } AS exercises,
              count { ()-[:HAS_CANDIDATE]->() } AS candidates,
              count { ()-[:LINKED_TO]->() } AS linked,
              count { ()-[:WORKS_ON]->() } AS works_on
        """).single()
    for k in row.keys():
        print(f"{k}: {row[k]}")
finally:
    driver.close()
