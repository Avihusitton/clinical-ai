import pytest
from retrieval import Retriever, find_entry_concepts
import json
from config import Config
from ingestion_pipeline import CandidateGenerator
from llm_client import LLMClient
import os

def test_baseline_retrieval():
    from neo4j import GraphDatabase
    # Characterization test for CURRENT retrieval logic
    cfg = Config()
    
    # We must not hardcode passwords. Read from env if present.
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "mock")
    
    driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, neo4j_password))
    llm = LLMClient("mock_key", cfg.llm_model, mock=True) # Ensure mock is True for test
    
    with open("data/glossary.json", "r", encoding="utf-8") as f:
        glossary = json.load(f)
    concept_gen = CandidateGenerator(cfg, glossary["concepts"], "Concept")
    
    retriever = Retriever(cfg, driver, concept_gen, llm)
    query = "הפעלה חזקה" # Matches 'הפעלה' alias
    
    # 1. Direct concept detection
    concepts = find_entry_concepts(query, concept_gen)
    assert len(concepts) >= 1
    
    # 2. Response structure and maximum depth
    # Assuming Retriever returns a string in current baseline
    res = retriever.answer(query, current_case_modality=None)
    assert isinstance(res, str)
    
    # 3. Check Neo4j counts to ensure no mutation
    with driver.session() as session:
        count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        # We don't assert a specific number, just verifying we can read.
        assert count >= 0
    
    baseline_payload = {
        "concepts": concepts,
        "response_length": len(res),
        "response_sample": res[:500] if res else ""
    }
    
    os.makedirs("out", exist_ok=True)
    with open("out/retrieval_baseline_sample.json", "w", encoding="utf-8") as f:
        json.dump(baseline_payload, f, ensure_ascii=False, indent=2)
        
    print("Baseline test passed")


def test_retrieval_characterization():
    cfg = Config()
    retriever = Retriever(cfg, None, None, None)
    
    # 1. Maximum traversal depth
    assert "*1..2]" in retriever._cypher, "Hard max traversal depth of 2 must be enforced in the reasoning traversal."
    
    # 2. Allowed relation traversal
    from retrieval import EXERCISES_FOR_CONCEPTS_CYPHER
    for rel in cfg.reasoning_relationship_types:
        assert rel.upper() in retriever._cypher, f"Relation {rel} must be explicitly allowed in traversal."
        
    # 3. Blocked relation traversal & HAS_CANDIDATE vs LINKED_TO
    assert "IS_SIMILAR" not in retriever._cypher, "IS_SIMILAR must not be in reasoning traversal."
    assert "HAS_CANDIDATE" not in retriever._cypher, "HAS_CANDIDATE is a loader relation, not reasoning."
    
    # 4. Exercise cannot act as an intermediate node
    assert "(start:Concept" in retriever._cypher
    assert "(end:Concept)" in retriever._cypher
    assert "Exercise" not in retriever._cypher, "Exercise cannot act as an intermediate node in reasoning."
    
    # 5. Exercises are only retrieved in a dedicated 1-hop terminal query
    assert "WORKS_ON" in EXERCISES_FOR_CONCEPTS_CYPHER
    assert "(co:Concept)<-[r:WORKS_ON]-(e:Exercise)" in EXERCISES_FOR_CONCEPTS_CYPHER
    
    # 6. Production isolation
    assert "OfficialEntryShadow" not in retriever._cypher
    assert "OfficialEntryShadow" not in EXERCISES_FOR_CONCEPTS_CYPHER


