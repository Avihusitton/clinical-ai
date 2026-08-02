from config import Config
from neo4j import GraphDatabase

cfg = Config()
driver = GraphDatabase.driver(
    cfg.neo4j_uri,
    auth=(cfg.neo4j_user, cfg.neo4j_password),
)

try:
    driver.verify_connectivity()

    with driver.session() as session:
        ping = session.run("RETURN 1 AS ok").single()["ok"]

        apoc = session.run(
            """
            SHOW PROCEDURES YIELD name
            WHERE name = 'apoc.merge.node'
            RETURN count(*) AS n
            """
        ).single()["n"]

    print("Neo4j connection:", "תקין" if ping == 1 else "נכשל")
    print("APOC apoc.merge.node:", "זמין" if apoc else "חסר")

finally:
    driver.close()
