import json
import sys
from config import Config
from neo4j import GraphDatabase

def main():
    cfg = Config()
    driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))
    
    baseline = {}
    
    with driver.session() as session:
        # Node counts
        baseline["nodes"] = {}
        res = session.run("MATCH (n) RETURN labels(n) as label, count(*) as c")
        for record in res:
            lbl = record["label"][0] if record["label"] else "Unlabeled"
            baseline["nodes"][lbl] = baseline["nodes"].get(lbl, 0) + record["c"]
            
        # Relationship counts
        baseline["relationships"] = {}
        res = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as c")
        for record in res:
            baseline["relationships"][record["type"]] = record["c"]
            
        # Constraints
        baseline["constraints"] = []
        try:
            res = session.run("SHOW CONSTRAINTS YIELD name, type, entityType, labelsOrTypes, properties")
            for record in res:
                baseline["constraints"].append(record.data())
        except Exception as e:
            baseline["constraints"].append(str(e))
            
        # Indexes
        baseline["indexes"] = []
        try:
            res = session.run("SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties")
            for record in res:
                baseline["indexes"].append(record.data())
        except Exception as e:
            baseline["indexes"].append(str(e))

    driver.close()
    
    with open("out/neo4j_baseline_stats.json", "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)
        
    print("Exported baseline to out/neo4j_baseline_stats.json")

if __name__ == "__main__":
    main()
