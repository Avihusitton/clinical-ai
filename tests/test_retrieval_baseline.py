import pytest
from retrieval import Retriever, find_entry_concepts
import json
from neo4j import GraphDatabase
from config import Config
from ingestion_pipeline import CandidateGenerator
from llm_client import LLMClient

def test_baseline_retrieval():
    # This test serves as a characterization test of the CURRENT retrieval logic before the glossary pilot.
    cfg = Config()
    driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))
    llm = LLMClient(cfg.openrouter_api_key, cfg.llm_model, mock=cfg.mock_llm)
    with open("data/glossary.json", "r", encoding="utf-8") as f:
        glossary = json.load(f)
    concept_gen = CandidateGenerator(cfg, glossary["concepts"], "Concept")
    
    retriever = Retriever(cfg, driver, concept_gen, llm)
    query = "פחד נטישה"
    
    # 1. Existing candidate matching behavior
    concepts = find_entry_concepts(query, concept_gen)
    
    # 2. Existing candidate matching behavior
    res = retriever.answer(query, current_case_modality=None)
    
    # Save the baseline payload for later comparison
    baseline_payload = {
        "concepts": concepts,
        "response_length": len(res),
        "response_sample": res[:500] if res else ""
    }
    
    with open("out/retrieval_baseline_sample.json", "w", encoding="utf-8") as f:
        json.dump(baseline_payload, f, ensure_ascii=False, indent=2)
        
    print("Baseline test passed and saved sample to out/retrieval_baseline_sample.json")
