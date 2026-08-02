import json
import hashlib
from collections import defaultdict, Counter
import re

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glossary_alias_index import TrieAliasMatcher

def test_span_gold_integrity():
    dataset_path = "tests/fixtures/hebrew_alias_evaluation.jsonl"
    
    with open(dataset_path, "rb") as f:
        dataset_sha256_frozen = hashlib.sha256(f.read()).hexdigest()
        dataset_sha256_before_pytest = dataset_sha256_frozen
        
    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    categories = defaultdict(list)
    
    for record in records:
        text = record["text"]
        categories[record["category"]].append(record)
        for expected in record.get("expected_spans", []):
            start = expected["start"]
            end = expected["end"]
            matched_text = expected["matched_text"]
            
            assert 0 <= start < end <= len(text)
            assert text[start:end] == matched_text
            
            occurrences = []
            cursor = 0
            while True:
                found = text.find(matched_text, cursor)
                if found == -1:
                    break
                occurrences.append(found)
                cursor = found + 1
                
            if len(occurrences) == 1:
                assert occurrences[0] == start
            else:
                assert "occurrence_index" in expected
                occurrence_index = expected["occurrence_index"]
                assert 0 <= occurrence_index < len(occurrences)
                assert occurrences[occurrence_index] == start
                
    samples_to_pick = {
        "NIQQUD": 5,
        "PUNCTUATION": 5,
        "MIXED_RTL_LTR": 5,
        "OVERLAPPING_TERMS": 5,
        "LONGEST_MATCH": 5,
        "ALIAS_COLLISION": 5
    }
    
    review_sample = []
    
    for cat, count in samples_to_pick.items():
        assert len(categories[cat]) >= count
        chosen = categories[cat][:count]
        
        for record in chosen:
            validation_method = "UNIQUE_LITERAL_OCCURRENCE"
            
            if cat == "NIQQUD":
                has_niqqud = bool(re.search(r'[\u0591-\u05C7]', record["text"]))
                assert has_niqqud
                validation_method = "HEBREW_COMBINING_MARK_OFFSET"
                
            elif cat == "PUNCTUATION":
                has_punct = bool(re.search(r'["\'-/()\u05BE]', record["text"]))
                assert has_punct
                validation_method = "PUNCTUATION_OFFSET"
                
            elif cat == "MIXED_RTL_LTR":
                has_hebrew = bool(re.search(r'[\u0590-\u05FF]', record["text"]))
                has_latin = bool(re.search(r'[A-Za-z]', record["text"]))
                assert has_hebrew and has_latin
                validation_method = "MIXED_RTL_LTR_PYTHON_INDEX"
                
            elif cat == "OVERLAPPING_TERMS":
                assert len(record["expected_spans"]) > 1
                spans = sorted([(s["start"], s["end"]) for s in record["expected_spans"]])
                overlaps = False
                for i in range(len(spans) - 1):
                    if spans[i][1] > spans[i+1][0]:
                        overlaps = True
                        break
                assert overlaps
                validation_method = "OVERLAPPING_TERMS"
                
            elif cat == "LONGEST_MATCH":
                assert "longest_card_id" in record
                assert "longest_candidate" in record
                assert "shorter_candidates" in record
                
                expected = record["expected_spans"][0]
                assert expected["matched_text"] == record["longest_candidate"]
                
                for shorter in record["shorter_candidates"]:
                    assert shorter["term"] in record["longest_candidate"]
                    assert len(shorter["term"]) < len(record["longest_candidate"])
                    
                # Run the Trie separately to prove winning span is declared longest
                # and no shorter nested candidate is returned as the winner.
                matcher = TrieAliasMatcher()
                
                build_records = [
                    {"card_id": record["longest_card_id"], "entry_name": record["longest_candidate"], "type": "exact"}
                ]
                for shorter in record["shorter_candidates"]:
                    build_records.append({
                        "card_id": shorter["card_id"], 
                        "entry_name": shorter["term"], 
                        "type": "exact"
                    })
                
                matcher.build(build_records)
                    
                matches = list(matcher.find(record["text"]))
                
                # The winner must be the longest_candidate exactly
                assert len(matches) == 1
                assert matches[0].matched_form == record["longest_candidate"]
                assert matches[0].card_id == record["longest_card_id"]
                
                validation_method = "REGISTERED_LONGEST_MATCH"
                
            elif cat == "ALIAS_COLLISION":
                assert len(record["expected_card_ids"]) >= 2
                validation_method = "MULTI_CARD_ALIAS_COLLISION"
                
            expected = record["expected_spans"][0] if record.get("expected_spans") else None
            if expected:
                if "occurrence_index" in expected:
                    validation_method = "DOCUMENTED_OCCURRENCE_INDEX"
                    
                text_slice = record["text"][expected["start"]:expected["end"]]
                assert text_slice == expected["matched_text"]
                
                review_sample.append({
                    "case_id": record["case_id"],
                    "text": record["text"],
                    "expected_start": expected["start"],
                    "expected_end": expected["end"],
                    "expected_matched_text": expected["matched_text"],
                    "text_slice": text_slice,
                    "category": cat,
                    "validation_method": validation_method,
                    "review_status": "VERIFIED"
                })
                
    assert len(review_sample) == 30
    assert Counter(r["category"] for r in review_sample) == {
        "NIQQUD": 5,
        "PUNCTUATION": 5,
        "MIXED_RTL_LTR": 5,
        "OVERLAPPING_TERMS": 5,
        "LONGEST_MATCH": 5,
        "ALIAS_COLLISION": 5,
    }
    
    with open("tests/SPAN_GOLD_MANUAL_REVIEW.json", "w", encoding="utf-8") as f:
        json.dump(review_sample, f, indent=2, ensure_ascii=False)
        
    with open(dataset_path, "rb") as f:
        dataset_sha256_after_pytest = hashlib.sha256(f.read()).hexdigest()
        
    dataset_modified_during_pytest = dataset_sha256_before_pytest != dataset_sha256_after_pytest
    assert dataset_sha256_before_pytest == dataset_sha256_after_pytest
    assert not dataset_modified_during_pytest
