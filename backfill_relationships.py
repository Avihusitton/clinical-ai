import os
import json
import datetime as dt
from neo4j import GraphDatabase
from dotenv import load_dotenv

from config import Config
from llm_client import LLMClient
from ingestion_pipeline import RelationshipExtractor, Chunk, Pipeline, TemporalStatus
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
log = logging.getLogger("backfill")

load_dotenv()
cfg = Config()

def backfill():
    uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "12345678")

    driver = GraphDatabase.driver(uri, auth=(user, password))

    query = """
    MATCH (c:Chunk)
    OPTIONAL MATCH (c)-[r:LINKED_TO]->(ent)
    RETURN c.chunk_id AS chunk_id, c.text AS text,
           collect({entity_type: labels(ent)[0], canonical: ent.canonical_name, matched_form: r.matched_form, method: r.method}) AS links
    """
    
    log.info("Fetching chunks from Neo4j...")
    with driver.session() as session:
        result = session.run(query)
        records = list(result)
    pipeline = Pipeline(cfg)
    extractor = pipeline.rel_extractor

    log.info(f"Found {len(records)} chunks in Neo4j. Extracting relationships...")
    
    rel_edges = []
    
    # Process only chunks that have at least 2 Concepts/Candidates
    for r in tqdm(records, desc="Extracting Relationships"):
        chunk_id = r["chunk_id"]
        text = r["text"]
        
        # Filter valid links
        links = [l for l in r["links"] if l.get("entity_type")]
        
        c = Chunk(
            chunk_id=chunk_id, 
            doc_id="dummy",
            text=text, 
            paragraph_range=(0,0),
            lesson_number=None,
            lesson_date=None,
            temporal_status=TemporalStatus.TIMELESS,
            anchor_distance=0,
            modality="text"
        )
        c.verified_links = links
        
        # Check if there are at least 2 concept/candidate entities
        concept_entities = [link for link in links if link["entity_type"] in ("Concept", "Candidate")]
        if len(concept_entities) < 2:
            continue
            
        to_load, conf = extractor.extract_concept_relationships(c, {})
        rel_edges.extend(to_load)

    log.info(f"Extracted {len(rel_edges)} relationships. Queuing them...")
    if rel_edges:
        pipeline._queue_concept_relationships(rel_edges)
        log.info("Done! Relationships queued successfully.")
    else:
        log.info("No relationships found. Nothing to queue.")

if __name__ == "__main__":
    backfill()
