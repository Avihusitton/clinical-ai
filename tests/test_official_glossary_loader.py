from official_glossary_loader import OfficialGlossaryLoader

class MockStore:
    def __init__(self, entries):
        self.entries = entries
    def get_all_entries(self):
        return self.entries

def test_loader_validation():
    store = MockStore([
        {"canonical_name": "Test"}, # Missing card_id
        {"card_id": "T1", "canonical_name": "Test1"},
        {"card_id": "T1", "canonical_name": "Test2"} # Duplicate
    ])
    loader = OfficialGlossaryLoader(store)
    errors = loader.validate()
    
    assert len(errors) == 2
    assert any("Missing card_id" in e for e in errors)
    assert any("Duplicate card_id" in e for e in errors)

def test_loader_dry_run():
    store = MockStore([
        {"card_id": "T1", "canonical_name": "Test1"}
    ])
    loader = OfficialGlossaryLoader(store)
    report = loader.dry_run()
    
    assert report["new_entries"] == 1
    assert report["duplicate_card_ids"] == 0
