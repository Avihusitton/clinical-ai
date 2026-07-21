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
            RETURN count(DISTINCT n) AS nodes, count(r) AS relationships
        """).single()
    print("לפני טעינה - nodes:", row["nodes"])
    print("לפני טעינה - relationships:", row["relationships"])
finally:
    driver.close()
