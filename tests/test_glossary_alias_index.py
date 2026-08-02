from glossary_alias_index import TrieAliasMatcher
import json
import os

def test_trie_alias_matcher_longest_match():
    # Make sure we don't fail if exceptions file is missing in test env
    if not os.path.exists("data/official_glossary"):
        os.makedirs("data/official_glossary", exist_ok=True)
    with open("data/official_glossary/alias_exceptions.json", "w", encoding="utf-8") as f:
        json.dump({"allow_short": [], "blocked": []}, f)
        
    matcher = TrieAliasMatcher()
    records = [
        {"card_id": "C001", "entry_name": "פחד", "aliases_and_spellings": []},
        {"card_id": "C002", "entry_name": "פחד נטישה", "aliases_and_spellings": []}
    ]
    matcher.build(records)
    
    matches = matcher.find("יש לו פחד נטישה חמור")
    assert len(matches) == 1
    assert matches[0].card_id == "C002"  # Should prefer longest match
    
def test_trie_alias_matcher_normalization():
    matcher = TrieAliasMatcher()
    records = [
        {"card_id": "C001", "entry_name": "פחד", "aliases_and_spellings": []}
    ]
    matcher.build(records)
    
    # Should ignore niqqud and preserve original string and offsets
    text = "הוא חווה פַּחַד מטורף"
    matches = matcher.find(text)
    assert len(matches) == 1
    assert matches[0].card_id == "C001"
    assert matches[0].matched_form == "פַּחַד"
