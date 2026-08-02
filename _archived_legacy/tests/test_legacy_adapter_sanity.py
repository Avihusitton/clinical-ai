import json
import pytest
from config import Config
from ingestion_pipeline import CandidateGenerator
from retrieval import find_entry_concepts

def test_legacy_adapter_sanity():
    # 1. Read actual canonical name from legacy glossary
    with open("data/glossary.json", "r", encoding="utf-8") as f:
        legacy_data = json.load(f)["concepts"]
        
    cfg = Config()
    legacy_gen = CandidateGenerator(cfg, legacy_data, "Concept")
    
    # Let's find 5 known concepts that don't suffer from alias collisions
    known_concepts = []
    for concept in legacy_data.keys():
        norm_concept = legacy_gen.normalizer.normalize_token(concept)
        if norm_concept in legacy_gen.form_to_canonical and legacy_gen.form_to_canonical[norm_concept].lower() == concept.lower():
            known_concepts.append(concept)
            if len(known_concepts) == 5:
                break
    
    known_positive_cases_passed = 0
    known_negative_cases_passed = 0
    
    report = {
        "legacy_class": "CandidateGenerator",
        "legacy_public_method": "find_entry_concepts",
        "known_positive_cases_total": len(known_concepts),
        "known_negative_cases_total": len(known_concepts),
        "cases": []
    }
    
    for concept in known_concepts:
        canonical = concept
        # Try a positive case
        input_sentence = f"This is a sentence containing {canonical} in the middle."
        results = find_entry_concepts(input_sentence, legacy_gen)
        
        # Check if canonical is in results
        is_positive_passed = any(res.lower() == canonical.lower() for res in results)
        if is_positive_passed:
            known_positive_cases_passed += 1
            
        # Try a negative case
        neg_sentence = "This sentence has completely unrelated words like elephant and computer."
        neg_results = find_entry_concepts(neg_sentence, legacy_gen)
        
        is_negative_passed = not any(res.lower() == canonical.lower() for res in neg_results)
        if is_negative_passed:
            known_negative_cases_passed += 1
            
        report["cases"].append({
            "input_example": input_sentence,
            "raw_output_example": list(results),
            "normalized_adapter_output": [r.lower() for r in results],
            "is_positive_passed": is_positive_passed
        })

    # Characterize known collision
    collision_input = "אנחנו צריכים הגנות"
    collision_results = find_entry_concepts(collision_input, legacy_gen)
    expected_legacy_resolution = "מנהלים"
    actual_legacy_resolution = collision_results[0] if collision_results else ""
    collision_status = "CHARACTERIZED" if expected_legacy_resolution in collision_results else "FAILED"
    
    report["known_collision"] = {
        "input_form": "הגנות",
        "expected_legacy_resolution": expected_legacy_resolution,
        "actual_legacy_resolution": actual_legacy_resolution,
        "collision_status": collision_status
    }
        
    report["known_positive_cases_passed"] = known_positive_cases_passed
    report["known_negative_cases_passed"] = known_negative_cases_passed
    report["known_collisions_characterized"] = 1 if collision_status == "CHARACTERIZED" else 0
    
    if known_positive_cases_passed == len(known_concepts) and known_negative_cases_passed == len(known_concepts) and collision_status == "CHARACTERIZED":
        report["adapter_status"] = "LEGACY_ADAPTER_VALIDATED"
    else:
        report["adapter_status"] = "LEGACY_ADAPTER_NEEDS_REFINEMENT"
        
    with open("tests/LEGACY_ADAPTER_SANITY_REPORT.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    assert known_positive_cases_passed == 5, f"Expected 5 positive passes, got {known_positive_cases_passed}"
    assert known_negative_cases_passed == 5, f"Expected 5 negative passes, got {known_negative_cases_passed}"
    assert collision_status == "CHARACTERIZED", f"Failed to characterize collision"
