import json
from neo4j import GraphDatabase
from config import Config
from pathlib import Path

cfg = Config()
driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))

concepts = {}
with driver.session() as session:
    res = session.run("MATCH (n) WHERE n:Concept OR n:Exercise RETURN labels(n)[0] as label, n.canonical_name as name")
    for r in res:
        name = r["name"]
        label = r["label"]
        if not name:
            continue
        c_type = "exercise" if label == "Exercise" else "concept"
        concepts[name] = {
            "parent": None,
            "synonyms": [],
            "definition": "",
            "type": c_type
        }

out_path = Path(cfg.output_dir) / "glossary_draft.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "source_document": "Restored from Neo4j",
        "status": "draft_requires_human_approval",
        "concepts": dict(sorted(concepts.items()))
    }, f, ensure_ascii=False, indent=2)

print(f"Restored {len(concepts)} concepts to glossary_draft.json")
