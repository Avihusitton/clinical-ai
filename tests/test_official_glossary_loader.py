from official_glossary_loader import OfficialGlossaryLoader

class MockStore:
    def __init__(self, entries):
        self.entries = entries
    def get_all_entries(self):
        return self.entries
    def validate(self):
        return []
    def get_alias_collisions(self):
        return {}

class MockDriver:
    class MockSession:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def run(self, query, **kwargs):
            class Result:
                def __iter__(self):
                    return iter([])
                def single(self):
                    return None
            return Result()
            
    def session(self):
        return self.MockSession()

def test_loader_dry_run():
    store = MockStore([
        {"card_id": "Z901", "entry_name": "Test1", "entry_type": "CONCEPT", "status": "APPROVED", "aliases_and_spellings": []}
    ])
    loader = OfficialGlossaryLoader(store, MockDriver())
    report = loader.dry_run("test_pilot")
    
    assert report["new_entries"] == 1
    assert report["duplicate_card_ids"] == 0
    assert report["unmapped_official_entries"] == 1
