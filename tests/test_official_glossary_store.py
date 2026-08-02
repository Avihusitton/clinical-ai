from official_glossary_store import OfficialGlossaryStore
from pathlib import Path
import json

def get_valid_record(card_id, entry_name):
    return {
        "card_id": card_id,
        "status": "APPROVED",
        "dictionary_version": "v1",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
        "entry_name": entry_name,
        "entry_type": "CONCEPT",
        "aliases_and_spellings": [],
        "source_based_definition": "",
        "unified_definition": "",
        "parent_terms": [],
        "child_terms": [],
        "parallel_terms": [],
        "distinguish_from": [],
        "causal_or_developmental_relations": [],
        "related_techniques": [],
        "related_exercises": [],
        "therapeutic_contexts": [],
        "short_example": "",
        "common_mistakes": "",
        "exact_source": "",
        "certainty": "HIGH",
        "editorial_note": "",
        "see_also": [],
        "card_hash": "1111111111111111111111111111111111111111111111111111111111111111"
    }

def test_store_loads_data(tmp_path):
    data_file = tmp_path / "test_glossary.jsonl"
    record1 = get_valid_record("Z901", "Test 1")
    record2 = get_valid_record("Z902", "Test 2")
    
    with open(data_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record1) + "\n")
        f.write(json.dumps(record2) + "\n")
        
    store = OfficialGlossaryStore(str(data_file))
    store.load()
    
    assert len(store.get_all_entries()) == 2
    assert store.get_by_card_id("Z901")["entry_name"] == "Test 1"
    assert store.get_by_card_id("Z903") is None

def test_hash_stability():
    from official_glossary_loader import OfficialGlossaryLoader
    loader = OfficialGlossaryLoader(None, None)
    
    record1 = {"card_id": "Z901", "status": "APPROVED", "entry_name": "Test"}
    record2 = {"entry_name": "Test", "status": "APPROVED", "card_id": "Z901"}
    assert loader._hash_record(record1) == loader._hash_record(record2)
    
    record3 = {**record1, "updated_at": "2023-01-01T00:00:00Z"}
    record4 = {**record1, "updated_at": "2024-01-01T00:00:00Z"}
    assert loader._hash_record(record3) == loader._hash_record(record4)

def test_schema_validation(tmp_path):
    data_file = tmp_path / "test_glossary.jsonl"
    record1 = get_valid_record("Z901", "Test")
    
    with open(data_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record1) + "\n")
        
    store = OfficialGlossaryStore(str(data_file))
    store.load()
    entries = store.get_all_entries()
    assert len(entries) == 1
    assert entries[0]["card_id"] == "Z901"
