"""
NEO4J STAGING INGESTION PACKAGE
================================
Full pipeline: source identity → preflight → dry-run → load → post-load validation.

Usage:
    python neo4j_staging/neo4j_staging_ingest.py [--dry-run] [--rollback BATCH_ID]
"""
import os
import sys
import json
import hashlib
import uuid
import datetime
import argparse
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
CONCEPT_DICT_PATH = REPO_ROOT / "data" / "glossary.json"
OFFICIAL_GLOSSARY_PATH = REPO_ROOT / "data" / "official_glossary" / "official_glossary.sample.jsonl"
DRY_RUN_PATH = REPO_ROOT / "tests" / "NEO4J_STAGING_DRY_RUN.json"
LOAD_EVIDENCE_PATH = REPO_ROOT / "tests" / "NEO4J_STAGING_LOAD_EVIDENCE.json"
POST_LOAD_PATH = REPO_ROOT / "tests" / "NEO4J_STAGING_POST_LOAD_VALIDATION.json"

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
SOURCE_VERSION = "1.0.0"
BATCH_SIZE = 50
STAGING_URI_MARKERS = {"staging", "stage", "dev", "test", "sandbox", "localhost", "127.0.0.1"}
STAGING_DB_MARKERS = {"staging", "stage", "development", "dev", "test", "sandbox"}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def make_batch_id(dict_sha: str, gloss_sha: str) -> str:
    seed = f"neo4j-staging-{dict_sha[:16]}-{gloss_sha[:16]}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

# ─────────────────────────────────────────────
# LOAD SOURCE DATA
# ─────────────────────────────────────────────
def load_concept_dictionary():
    raw = CONCEPT_DICT_PATH.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw.decode("utf-8"))
    concepts_raw = data.get("concepts", {})

    records = []
    idx = 1
    for term, details in concepts_raw.items():
        cid = f"CONCEPT-{idx:03d}"
        idx += 1
        pref_term = term.strip()
        defn = details.get("definition", "").strip()
        synonyms = details.get("synonyms", [])
        parent = details.get("parent")
        if parent:
            parent = parent.strip()

        # compute content sha
        content = json.dumps({
            "preferred_term": pref_term,
            "definition": defn,
            "aliases": sorted(synonyms),
            "parent": parent
        }, sort_keys=True, ensure_ascii=False)
        content_sha = sha256_str(content)

        records.append({
            "concept_id": cid,
            "preferred_term": pref_term,
            "definition": defn,
            "aliases": synonyms,
            "category": "concept",
            "status": "ACTIVE",
            "source": "data/glossary.json",
            "source_version": SOURCE_VERSION,
            "parent": parent,
            "content_sha256": content_sha,
        })
    return records, sha

def load_official_glossary():
    raw = OFFICIAL_GLOSSARY_PATH.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    entries = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if line:
            entry = json.loads(line)
            content = json.dumps({k: v for k, v in entry.items()}, sort_keys=True, ensure_ascii=False)
            entry["content_sha256"] = sha256_str(content)
            entries.append(entry)
    return entries, sha

# ─────────────────────────────────────────────
# PREFLIGHT CHECKS
# ─────────────────────────────────────────────
def run_preflight(concepts, glossary_entries):
    errors = []
    warnings = []

    concept_ids = {}
    preferred_terms = {}
    all_pref_terms = {c["preferred_term"] for c in concepts}

    for c in concepts:
        cid = c["concept_id"]
        pt = c["preferred_term"]
        defn = c["definition"]
        parent = c["parent"]

        # Dup concept IDs
        if cid in concept_ids:
            errors.append(f"DUPLICATE_ID: {cid}")
        concept_ids[cid] = pt

        # Dup preferred terms
        if pt in preferred_terms:
            errors.append(f"DUPLICATE_PREF_TERM: {pt}")
        preferred_terms[pt] = cid

        # Empty required fields
        if not pt or not defn:
            errors.append(f"EMPTY_REQUIRED: cid={cid} pt='{pt}'")

        # Self-relation
        if parent and parent == pt:
            warnings.append(f"SELF_RELATION: '{pt}' points to itself as parent")

        # Broken relationship target
        if parent and parent != pt and parent not in all_pref_terms:
            errors.append(f"BROKEN_REL: '{pt}' -> parent='{parent}' not found")

        # UTF-8
        try:
            pt.encode("utf-8").decode("utf-8")
            defn.encode("utf-8").decode("utf-8")
        except Exception as e:
            errors.append(f"UTF8: cid={cid}: {e}")

    # PII checks (dictionary)
    email_re = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    phone_re = re.compile(r'\b(?:\+?972[-_ ]?|0)(?:[23489]|5[0-9])[-_ ]?\d{3}[-_ ]?\d{4}\b')
    id_re = re.compile(r'\b\d{9}\b')
    for c in concepts:
        text = f"{c['preferred_term']} {c['definition']} {' '.join(c['aliases'])}"
        if email_re.search(text) or phone_re.search(text) or id_re.search(text):
            errors.append(f"PII_DETECTED: cid={c['concept_id']}")

    # Glossary checks
    glossary_ids = set()
    for e in glossary_entries:
        card_id = e.get("card_id", "")
        cname = e.get("canonical_name", "")
        defn = e.get("definition", "")
        if not card_id or not cname or not defn:
            errors.append(f"GLOSSARY_EMPTY_FIELD: card_id={card_id}")
        if card_id in glossary_ids:
            errors.append(f"GLOSSARY_DUPLICATE_ID: {card_id}")
        glossary_ids.add(card_id)
        text = f"{card_id} {cname} {defn} {' '.join(e.get('aliases', []))}"
        if email_re.search(text) or phone_re.search(text) or id_re.search(text):
            errors.append(f"GLOSSARY_PII: card={card_id}")

    return errors, warnings

# ─────────────────────────────────────────────
# NEO4J CONNECTION
# ─────────────────────────────────────────────
def get_driver():
    import neo4j
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    return neo4j.GraphDatabase.driver(uri, auth=(user, password))

def verify_staging_target(driver, database):
    """Returns (is_staging, db_name)"""
    uri = (os.environ.get("NEO4J_URI", "")).lower()
    db_lower = database.lower()
    uri_is_staging = any(m in uri for m in STAGING_URI_MARKERS)
    db_is_staging = any(m in db_lower for m in STAGING_DB_MARKERS)
    return uri_is_staging or db_is_staging, database

# ─────────────────────────────────────────────
# CONSTRAINTS
# ─────────────────────────────────────────────
CONSTRAINTS = [
    "CREATE CONSTRAINT concept_concept_id_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.concept_id IS UNIQUE",
    "CREATE CONSTRAINT glossaryentry_card_id_unique IF NOT EXISTS FOR (g:GlossaryEntry) REQUIRE g.card_id IS UNIQUE",
    "CREATE CONSTRAINT category_name_unique IF NOT EXISTS FOR (cat:Category) REQUIRE cat.name IS UNIQUE",
    "CREATE CONSTRAINT source_name_unique IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE",
]

# ─────────────────────────────────────────────
# DRY RUN
# ─────────────────────────────────────────────
def generate_dry_run(concepts, glossary_entries, batch_id, dict_sha, gloss_sha):
    concept_term_to_id = {c["preferred_term"]: c["concept_id"] for c in concepts}
    
    nodes_to_create = []
    relationships_to_create = []
    records_rejected = 0
    self_relation_count = 0

    for c in concepts:
        nodes_to_create.append({
            "type": "Concept",
            "concept_id": c["concept_id"],
            "preferred_term": c["preferred_term"],
            "status": c["status"],
        })

    for e in glossary_entries:
        nodes_to_create.append({
            "type": "GlossaryEntry",
            "card_id": e["card_id"],
            "canonical_name": e["canonical_name"],
        })

    # Relationships
    all_terms = {c["preferred_term"] for c in concepts}
    for c in concepts:
        parent = c.get("parent")
        if parent:
            if parent == c["preferred_term"]:
                # Self-relation — skip, flag as warning (not rejected)
                self_relation_count += 1
            elif parent in all_terms:
                child_id = c["concept_id"]
                parent_id = concept_term_to_id[parent]
                relationships_to_create.append({
                    "type": "CHILD_OF",
                    "from": child_id,
                    "to": parent_id,
                })

    # Batch count
    estimated_batches = (len(concepts) // BATCH_SIZE) + 1 + 1  # +1 glossary batch

    dry_run = {
        "ingestion_batch_id": batch_id,
        "input_dict_sha256": dict_sha,
        "input_gloss_sha256": gloss_sha,
        "generated_at": now_iso(),
        "nodes_to_create": len(nodes_to_create),
        "nodes_to_update": 0,
        "relationships_to_create": len(relationships_to_create),
        "constraints_to_create": len(CONSTRAINTS),
        "records_rejected": records_rejected,
        "self_relations_skipped": self_relation_count,
        "estimated_batch_count": estimated_batches,
        "dry_run_errors": 0,
        "node_breakdown": {
            "Concept": len(concepts),
            "GlossaryEntry": len(glossary_entries),
        },
        "relationship_breakdown": {
            "CHILD_OF": len([r for r in relationships_to_create if r["type"] == "CHILD_OF"]),
        }
    }
    return dry_run, relationships_to_create

# ─────────────────────────────────────────────
# LOAD — CONCEPTS
# ─────────────────────────────────────────────
def load_concepts(session, concepts, batch_id, database):
    total = 0
    for i in range(0, len(concepts), BATCH_SIZE):
        batch = concepts[i:i + BATCH_SIZE]
        params = [{
            "concept_id": c["concept_id"],
            "preferred_term": c["preferred_term"],
            "definition": c["definition"],
            "aliases": c["aliases"],
            "category": c["category"],
            "status": c["status"],
            "source": c["source"],
            "source_version": c["source_version"],
            "content_sha256": c["content_sha256"],
            "ingestion_batch_id": batch_id,
            "ingested_at": now_iso(),
        } for c in batch]

        session.run("""
            UNWIND $batch AS row
            MERGE (c:Concept {concept_id: row.concept_id})
            SET c.preferred_term = row.preferred_term,
                c.definition = row.definition,
                c.aliases = row.aliases,
                c.category = row.category,
                c.status = row.status,
                c.source = row.source,
                c.source_version = row.source_version,
                c.content_sha256 = row.content_sha256,
                c.ingestion_batch_id = row.ingestion_batch_id,
                c.ingested_at = row.ingested_at
        """, {"batch": params})
        total += len(batch)
    return total

# ─────────────────────────────────────────────
# LOAD — GLOSSARY ENTRIES
# ─────────────────────────────────────────────
def load_glossary_entries(session, entries, batch_id):
    params = [{
        "card_id": e["card_id"],
        "canonical_name": e["canonical_name"],
        "definition": e.get("definition", ""),
        "aliases": e.get("aliases", []),
        "status": e.get("status", "APPROVED"),
        "content_sha256": e["content_sha256"],
        "ingestion_batch_id": batch_id,
        "ingested_at": now_iso(),
    } for e in entries]

    session.run("""
        UNWIND $batch AS row
        MERGE (g:GlossaryEntry {card_id: row.card_id})
        SET g.canonical_name = row.canonical_name,
            g.definition = row.definition,
            g.aliases = row.aliases,
            g.status = row.status,
            g.content_sha256 = row.content_sha256,
            g.ingestion_batch_id = row.ingestion_batch_id,
            g.ingested_at = row.ingested_at
    """, {"batch": params})
    return len(params)

# ─────────────────────────────────────────────
# LOAD — RELATIONSHIPS
# ─────────────────────────────────────────────
def load_relationships(session, relationships, batch_id):
    if not relationships:
        return 0
    params = [{
        "from_id": r["from"],
        "to_id": r["to"],
        "ingestion_batch_id": batch_id,
        "created_at": now_iso(),
    } for r in relationships]

    session.run("""
        UNWIND $batch AS row
        MATCH (child:Concept {concept_id: row.from_id})
        MATCH (parent:Concept {concept_id: row.to_id})
        MERGE (child)-[r:CHILD_OF]->(parent)
        SET r.ingestion_batch_id = row.ingestion_batch_id,
            r.created_at = row.created_at
    """, {"batch": params})
    return len(params)

# ─────────────────────────────────────────────
# POST-LOAD VALIDATION
# ─────────────────────────────────────────────
def post_load_validate(session, concepts, glossary_entries, relationships, batch_id):
    errors = []

    # Count concepts
    r = session.run("MATCH (c:Concept) RETURN count(c) AS n")
    loaded_concept_count = r.single()["n"]

    # Count glossary entries
    r = session.run("MATCH (g:GlossaryEntry) RETURN count(g) AS n")
    loaded_glossary_count = r.single()["n"]

    # Count relationships by type
    r = session.run("MATCH ()-[rel:CHILD_OF]->() RETURN count(rel) AS n")
    loaded_child_of_count = r.single()["n"]

    # Duplicate concept IDs
    r = session.run("""
        MATCH (c:Concept)
        WITH c.concept_id AS cid, count(*) AS cnt
        WHERE cnt > 1
        RETURN count(*) AS dups
    """)
    dup_concept_ids = r.single()["dups"]
    if dup_concept_ids > 0:
        errors.append(f"DUPLICATE_CONCEPT_IDS: {dup_concept_ids}")

    # Missing required properties
    r = session.run("""
        MATCH (c:Concept)
        WHERE c.concept_id IS NULL OR c.preferred_term IS NULL 
              OR c.definition IS NULL OR c.status IS NULL
        RETURN count(c) AS n
    """)
    missing_props = r.single()["n"]
    if missing_props > 0:
        errors.append(f"MISSING_REQUIRED_PROPS: {missing_props}")

    # Broken relationships (dangling)
    r = session.run("""
        MATCH (c:Concept)-[:CHILD_OF]->(p)
        WHERE NOT p:Concept
        RETURN count(*) AS n
    """)
    broken_rels = r.single()["n"]
    if broken_rels > 0:
        errors.append(f"BROKEN_RELATIONSHIPS: {broken_rels}")

    # Orphan concepts (no relationship at all)
    r = session.run("""
        MATCH (c:Concept)
        WHERE NOT (c)-[:CHILD_OF]->() AND NOT ()-[:CHILD_OF]->(c)
        RETURN count(c) AS n
    """)
    orphan_count = r.single()["n"]

    # Records with current batch ID
    r = session.run("""
        MATCH (n) WHERE n.ingestion_batch_id = $bid
        RETURN count(n) AS n
    """, {"bid": batch_id})
    batch_tagged = r.single()["n"]

    # Deterministic sample
    r = session.run("""
        MATCH (c:Concept) 
        WHERE c.ingestion_batch_id = $bid
        RETURN c.concept_id AS cid, c.preferred_term AS term
        ORDER BY c.concept_id
        LIMIT 5
    """, {"bid": batch_id})
    sample = [dict(record) for record in r]

    # Validate expected counts
    if loaded_concept_count < len(concepts):
        errors.append(f"CONCEPT_COUNT_MISMATCH: loaded={loaded_concept_count} expected>={len(concepts)}")
    if dup_concept_ids != 0:
        errors.append("DUP_IDS_POST_LOAD_FAIL")

    return {
        "loaded_concept_count": loaded_concept_count,
        "loaded_glossary_entry_count": loaded_glossary_count,
        "loaded_relationship_count": {
            "CHILD_OF": loaded_child_of_count,
        },
        "duplicate_concept_ids": dup_concept_ids,
        "missing_required_properties": missing_props,
        "broken_relationships": broken_rels,
        "orphan_concepts": orphan_count,
        "records_with_batch_id": batch_tagged,
        "records_rejected": 0,
        "deterministic_sample": sample,
        "post_load_validation_errors": len(errors),
        "errors": errors,
    }

# ─────────────────────────────────────────────
# ROLLBACK
# ─────────────────────────────────────────────
def rollback(session, batch_id):
    """
    Remove only nodes and relationships tagged with this ingestion_batch_id.
    Does NOT use MATCH (n) DETACH DELETE n.
    """
    # Remove relationships first
    session.run("""
        MATCH ()-[r:CHILD_OF]->()
        WHERE r.ingestion_batch_id = $bid
        DELETE r
    """, {"bid": batch_id})

    # Remove Concept nodes
    session.run("""
        MATCH (c:Concept)
        WHERE c.ingestion_batch_id = $bid
        DETACH DELETE c
    """, {"bid": batch_id})

    # Remove GlossaryEntry nodes
    session.run("""
        MATCH (g:GlossaryEntry)
        WHERE g.ingestion_batch_id = $bid
        DETACH DELETE g
    """, {"bid": batch_id})

    print(f"ROLLBACK COMPLETE for batch_id={batch_id}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Neo4j Staging Ingestion Package")
    parser.add_argument("--dry-run", action="store_true", help="Generate dry-run only, no DB writes")
    parser.add_argument("--rollback", metavar="BATCH_ID", help="Rollback a previous ingestion by batch ID")
    args = parser.parse_args()

    print("=== NEO4J STAGING INGESTION ===")
    print(f"Mode: {'DRY-RUN' if args.dry_run else ('ROLLBACK' if args.rollback else 'LIVE')}")

    # Load data
    print("\n[1] Loading source data...")
    concepts, dict_sha = load_concept_dictionary()
    glossary_entries, gloss_sha = load_official_glossary()
    print(f"  Concepts: {len(concepts)}, Glossary entries: {len(glossary_entries)}")

    # Batch ID
    batch_id = make_batch_id(dict_sha, gloss_sha)
    print(f"  Ingestion batch ID: {batch_id}")

    # Preflight
    print("\n[2] Running preflight validation...")
    errors, warnings = run_preflight(concepts, glossary_entries)
    print(f"  Errors: {len(errors)}, Warnings: {len(warnings)}")
    if errors:
        print("  BLOCKING ERRORS:")
        for e in errors:
            print(f"    - {e}")
        print("BLOCKED: preflight failed. Cannot proceed.")
        sys.exit(1)
    if warnings:
        print("  Warnings (non-blocking):")
        for w in warnings:
            print(f"    - {w}")

    # Dry run
    print("\n[3] Generating dry run...")
    dry_run, relationships = generate_dry_run(concepts, glossary_entries, batch_id, dict_sha, gloss_sha)
    DRY_RUN_PATH.write_text(json.dumps(dry_run, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Dry run saved to: {DRY_RUN_PATH}")
    print(f"  Nodes to create: {dry_run['nodes_to_create']}")
    print(f"  Relationships to create: {dry_run['relationships_to_create']}")
    print(f"  Records rejected: {dry_run['records_rejected']}")
    print(f"  Dry run errors: {dry_run['dry_run_errors']}")

    if args.dry_run:
        print("\nDRY-RUN mode — no database writes.")
        return batch_id, dry_run, None, None

    # Database setup
    print("\n[4] Connecting to Neo4j staging...")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    driver = get_driver()
    driver.verify_connectivity()
    print("  Connectivity: OK")

    is_staging, db_name = verify_staging_target(driver, database)
    if not is_staging:
        driver.close()
        print("BLOCKED: Target does not appear to be staging.")
        sys.exit(2)
    print(f"  Staging target verified: {db_name}")

    # Rollback mode
    if args.rollback:
        print(f"\n[ROLLBACK] Rolling back batch: {args.rollback}")
        with driver.session(database=database) as session:
            rollback(session, args.rollback)
        driver.close()
        return

    # Load
    print("\n[5] Creating constraints...")
    with driver.session(database=database) as session:
        for cypher in CONSTRAINTS:
            try:
                session.run(cypher)
                print(f"  OK: {cypher[:60]}...")
            except Exception as e:
                print(f"  WARN: {e}")

    print("\n[6] Loading concepts...")
    with driver.session(database=database) as session:
        loaded_concepts = load_concepts(session, concepts, batch_id, database)
    print(f"  Loaded: {loaded_concepts}")

    print("\n[7] Loading glossary entries...")
    with driver.session(database=database) as session:
        loaded_glossary = load_glossary_entries(session, glossary_entries, batch_id)
    print(f"  Loaded: {loaded_glossary}")

    print("\n[8] Loading relationships (after all nodes exist)...")
    with driver.session(database=database) as session:
        loaded_rels = load_relationships(session, relationships, batch_id)
    print(f"  Loaded: {loaded_rels} CHILD_OF relationships")

    # Post-load validation
    print("\n[9] Post-load validation...")
    with driver.session(database=database) as session:
        plv = post_load_validate(session, concepts, glossary_entries, relationships, batch_id)

    plv["ingestion_batch_id"] = batch_id
    plv["dict_sha256"] = dict_sha
    plv["gloss_sha256"] = gloss_sha
    plv["validated_at"] = now_iso()
    plv["rollback_available"] = True
    plv["rollback_command"] = f"python neo4j_staging/neo4j_staging_ingest.py --rollback {batch_id}"

    POST_LOAD_PATH.write_text(json.dumps(plv, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Post-load validation saved to: {POST_LOAD_PATH}")
    print(f"  Post-load errors: {plv['post_load_validation_errors']}")

    driver.close()

    if plv["post_load_validation_errors"] > 0:
        print("\nFINAL_STATUS: BLOCKED_STAGING_LOAD_VALIDATION_FAILED")
    else:
        print(f"\nFINAL_STATUS: NEO4J_STAGING_LOAD_PASS")
        print(f"INGESTION_BATCH_ID: {batch_id}")
        print(f"LOADED_CONCEPT_COUNT: {plv['loaded_concept_count']}")
        print(f"LOADED_GLOSSARY_ENTRY_COUNT: {plv['loaded_glossary_entry_count']}")
        print(f"LOADED_RELATIONSHIP_COUNT: {plv['loaded_relationship_count']}")
        print(f"ROLLBACK_AVAILABLE: True")
        print(f"ROLLBACK_COMMAND: python neo4j_staging/neo4j_staging_ingest.py --rollback {batch_id}")

    return batch_id, dry_run, plv, loaded_rels

if __name__ == "__main__":
    main()
