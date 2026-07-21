from official_glossary_store import OfficialGlossaryStore
from pathlib import Path
import json

def test_store_loads_data(tmp_path):
    # Setup test data
    data_file = tmp_path / "test_glossary.jsonl"
    record1 = {"card_id": "T1", "canonical_name": "Test 1", "aliases": [], "definition": "def 1", "status": "APPROVED"}
    record2 = {"card_id": "T2", "canonical_name": "Test 2", "aliases": [], "definition": "def 2", "status": "APPROVED"}
    
    with open(data_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record1) + "\n")
        f.write(json.dumps(record2) + "\n")
        
    store = OfficialGlossaryStore(str(data_file))
    
    assert len(store.get_all_entries()) == 2
    assert store.get_entry("T1")["canonical_name"] == "Test 1"
    assert store.get_entry("T3") is None
