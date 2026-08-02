import json
import pytest

def test_evaluation_dataset_contract():
    records = []
    with open("tests/fixtures/hebrew_alias_evaluation.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    assert len(records) == 180, f"Expected exactly 180 records, got {len(records)}"
    
    category_counts = {}
    case_ids = set()
    
    for r in records:
        assert r["case_id"] not in case_ids, f"Duplicate case ID: {r['case_id']}"
        case_ids.add(r["case_id"])
        
        cat = r["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
        
        if len(r["expected_card_ids"]) == 0:
            assert len(r["expected_spans"]) == 0, f"Negative case {r['case_id']} has expected spans"
            
        for span in r["expected_spans"]:
            assert "card_id" in span
            assert "start" in span
            assert "end" in span
            assert "matched_text" in span
            
    expected_counts = {
        "LONGEST_MATCH": 25,
        "WORD_BOUNDARY": 25,
        "NIQQUD": 20,
        "PUNCTUATION": 20,
        "MIXED_RTL_LTR": 20,
        "OVERLAPPING_TERMS": 20,
        "UNSAFE_SHORT_ALIAS": 20,
        "NEGATIVE_FALSE_POSITIVE": 20,
        "ALIAS_COLLISION": 10
    }
    
    for cat, count in expected_counts.items():
        assert category_counts.get(cat, 0) == count, f"Expected {count} for {cat}, got {category_counts.get(cat, 0)}"
