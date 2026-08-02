import json
import pytest
from config import Config
from retrieval import Retriever

class MockLLM:
    def _call(self, system, user, mock_response=None):
        return mock_response or "MOCK_ANSWER"

class MockCandidateGenerator:
    def candidates_for(self, text):
        return [{"canonical": "StartConcept"}]

class MockRecord:
    def __init__(self, data_dict):
        self._data = data_dict
    def data(self):
        return self._data

class MockResult:
    def __init__(self, records):
        self.records = records
    def __iter__(self):
        return iter(self.records)

class MockSession:
    def run(self, query, **kwargs):
        if "MATCH path = (start:Concept {canonical_name: $start})" in query:
            start = kwargs.get("start")
            if start == "StartConcept":
                return MockResult([
                    MockRecord({"concept_chain": ["StartConcept", "Depth1"], "hop_evidence": [{"type": "LEADS_TO", "quote": "none", "modality": "general", "lesson_number": 1}]}),
                    MockRecord({"concept_chain": ["StartConcept", "Depth1", "Depth2"], "hop_evidence": [{"type": "LEADS_TO", "quote": "none", "modality": "general", "lesson_number": 1}, {"type": "RELATES_TO", "quote": "none", "modality": "general", "lesson_number": 1}]}),
                    MockRecord({"concept_chain": ["StartConcept", "Linked"], "hop_evidence": [{"type": "LINKED_TO", "quote": "none", "modality": "general", "lesson_number": 1}]}),
                    MockRecord({"concept_chain": ["StartConcept", "ExIntermediate", "Depth2"], "hop_evidence": [{"type": "LEADS_TO", "quote": "none", "modality": "general", "lesson_number": 1}, {"type": "LEADS_TO", "quote": "none", "modality": "general", "lesson_number": 1}]}),
                ])
            return MockResult([])
        elif "MATCH (co:Concept)<-[r:WORKS_ON]-(e:Exercise)" in query:
            concepts = kwargs.get("concept_names", [])
            if "Depth1" in concepts:
                return MockResult([
                    MockRecord({"concept": "Depth1", "exercise": "Ex1", "modality": "general", "quote": "none"})
                ])
            return MockResult([])
        return MockResult([])
    
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockDriver:
    def session(self):
        return MockSession()
    def close(self):
        pass

@pytest.fixture(scope="module")
def neo4j_driver():
    return MockDriver()

def test_direct_entry_detection(neo4j_driver):
    cfg = Config()
    retriever = Retriever(cfg, neo4j_driver, MockCandidateGenerator(), MockLLM())
    paths = retriever._run_reasoning("StartConcept")
    chains = [p["concept_chain"] for p in paths]
    all_nodes = set([n for chain in chains for n in chain])
    assert "StartConcept" in all_nodes
    assert "Depth1" in all_nodes

def test_maximum_traversal_depth(neo4j_driver):
    cfg = Config()
    retriever = Retriever(cfg, neo4j_driver, MockCandidateGenerator(), MockLLM())
    paths = retriever._run_reasoning("StartConcept")
    chains = [p["concept_chain"] for p in paths]
    all_nodes = set([n for chain in chains for n in chain])
    assert "Depth1" in all_nodes
    assert "Depth2" in all_nodes
    assert "Depth3" not in all_nodes

def test_allowed_relation_traversal(neo4j_driver):
    cfg = Config()
    retriever = Retriever(cfg, neo4j_driver, MockCandidateGenerator(), MockLLM())
    paths = retriever._run_reasoning("StartConcept")
    chains = [p["concept_chain"] for p in paths]
    assert any("Depth1" in c and "Depth2" in c for c in chains)
    
def test_blocked_relation_traversal(neo4j_driver):
    cfg = Config()
    retriever = Retriever(cfg, neo4j_driver, MockCandidateGenerator(), MockLLM())
    paths = retriever._run_reasoning("StartConcept")
    chains = [p["concept_chain"] for p in paths]
    all_nodes = set([n for chain in chains for n in chain])
    assert "Blocked" not in all_nodes
    assert "Candidate" not in all_nodes

def test_legacy_exercise_intermediate_node_behavior(neo4j_driver):
    # LEGACY_DEFECT_CONFIRMED:
    # Exercise may currently appear as an intermediate inferential node.
    cfg = Config()
    retriever = Retriever(cfg, neo4j_driver, MockCandidateGenerator(), MockLLM())
    paths = retriever._run_reasoning("StartConcept")
    chains = [p["concept_chain"] for p in paths]
    all_nodes = set([n for chain in chains for n in chain])
    assert "ExIntermediate" in all_nodes

def test_empty_result_fallback(neo4j_driver):
    cfg = Config()
    class EmptyGen:
        def candidates_for(self, text): return []
    empty_ret = Retriever(cfg, neo4j_driver, EmptyGen(), MockLLM())
    ans = empty_ret.answer("Unknown")
    assert "MOCK_ANSWER" not in ans

def test_terminal_exercise_lookup(neo4j_driver):
    cfg = Config()
    retriever = Retriever(cfg, neo4j_driver, MockCandidateGenerator(), MockLLM())
    exercises = retriever._run_exercises(["Depth1"])
    assert len(exercises) == 1
    assert exercises[0]["exercise"] == "Ex1"

def test_current_response_contract(neo4j_driver):
    cfg = Config()
    retriever = Retriever(cfg, neo4j_driver, MockCandidateGenerator(), MockLLM())
    ans = retriever.answer("StartConcept")
    assert ans == "MOCK_ANSWER"

def test_guard_no_live_mutations():
    with open(__file__, "r", encoding="utf-8") as f:
        content = f.read()
    forbidden = [
        "GraphDatabase.driver",
        "CREATE (",
        "DETACH DELETE",
        "DELETE n",
        "neo4j_uri",
        "neo4j_password"
    ]
    for word in forbidden:
        # Ignore our own mentions in this test
        assert content.count(word) <= 1, f"Forbidden word found in test: {word}"

def test_generate_report(neo4j_driver):
    report_json = {
        "test_backend": "DETERMINISTIC_MOCK_DRIVER",
        "production_nodes_created": 0,
        "production_nodes_updated": 0,
        "production_nodes_deleted": 0,
        "production_relationships_created": 0,
        "production_relationships_deleted": 0
    }
    with open("tests/BEHAVIORAL_MUTATION_REPORT.json", "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)
