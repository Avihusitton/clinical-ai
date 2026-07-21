from glossary_alias_index import TrieAliasMatcher

def test_trie_alias_matcher_longest_match():
    matcher = TrieAliasMatcher()
    records = [
        {"card_id": "C1", "canonical_name": "פחד", "aliases": []},
        {"card_id": "C2", "canonical_name": "פחד נטישה", "aliases": []}
    ]
    matcher.build(records)
    
    matches = matcher.find("יש לו פחד נטישה חמור")
    assert len(matches) == 1
    assert matches[0].card_id == "C2"  # Should prefer longest match
    
def test_trie_alias_matcher_normalization():
    matcher = TrieAliasMatcher()
    records = [
        {"card_id": "C1", "canonical_name": "פחד", "aliases": []}
    ]
    matcher.build(records)
    
    # Should ignore niqqud
    matches = matcher.find("פַּחַד מטורף")
    assert len(matches) == 1
    assert matches[0].card_id == "C1"
    assert matches[0].matched_form == "פחד"
