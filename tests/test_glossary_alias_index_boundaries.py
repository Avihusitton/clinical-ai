import pytest
from glossary_alias_index import TrieAliasMatcher

@pytest.fixture
def store_mock():
    class MockStore:
        def get_all_entries(self):
            return [
                {
                    "card_id": "Z901",
                    "entry_name": "פחד",
                    "aliases_and_spellings": ["הזדהות"]
                },
                {
                    "card_id": "Z902",
                    "entry_name": "פחד נטישה",
                    "aliases_and_spellings": []
                }
            ]
    return MockStore()

def test_trie_boundaries(store_mock):
    matcher = TrieAliasMatcher("data/official_glossary/alias_exceptions.json")
    matcher.build(store_mock.get_all_entries())
    
    # 1. Exact match
    res = matcher.find("פחד")
    assert len(res) == 1
    assert res[0].canonical_name == "פחד"
    
    # 2. Prefixed invalid boundary (should NOT match 'פחד')
    res = matcher.find("מפחד")
    assert len(res) == 0
    
    # 3. Prefixed invalid boundary 2
    res = matcher.find("הפחד")
    assert len(res) == 0
    
    # 4. No space between words
    res = matcher.find("פחדנטישה")
    assert len(res) == 0
    
    # 5. Punctuation boundary (valid)
    res = matcher.find("פחד-נטישה")
    assert len(res) == 1
    assert res[0].canonical_name == "פחד נטישה"
    
    # 6. Space boundary (valid)
    res = matcher.find("פחד נטישה")
    assert len(res) == 1
    assert res[0].canonical_name == "פחד נטישה"
    
    # 7. Prefix boundary check
    res = matcher.find("חוסר הזדהות")
    assert len(res) == 1
    assert res[0].canonical_name == "פחד" # matches alias 'הזדהות'
    
    # 8. Exact alias
    res = matcher.find("הזדהות")
    assert len(res) == 1
    assert res[0].canonical_name == "פחד"
