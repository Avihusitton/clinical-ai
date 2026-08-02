import json
import time
from collections import defaultdict
from config import Config
from ingestion_pipeline import CandidateGenerator
from official_glossary_store import OfficialGlossaryStore
from glossary_alias_index import TrieAliasMatcher

# Load legacy glossary data
with open("data/glossary.json", "r", encoding="utf-8") as f:
    legacy_glossary = json.load(f)

# Initialize legacy generator
cfg = Config()
legacy_gen = CandidateGenerator(cfg, legacy_glossary["concepts"], "Concept")

# Load new official glossary format for Trie
# For the evaluation dataset, we'll map Z901 to "פחד נטישה" and Z902 to "הזדהות השלכתית"
trie_matcher = TrieAliasMatcher()
mock_records = [
    {
        "card_id": "Z901",
        "entry_name": "פחד נטישה",
        "aliases_and_spellings": ["חרדת נטישה"],
        "status": "APPROVED",
        "entry_type": "CONCEPT"
    },
    {
        "card_id": "Z902",
        "entry_name": "הזדהות השלכתית",
        "aliases_and_spellings": ["הזדהות", "הזדהות פרויקטיבית"],
        "status": "APPROVED",
        "entry_type": "CONCEPT"
    }
]
trie_matcher.build(mock_records)

def load_eval_data():
    data = []
    with open("tests/fixtures/hebrew_alias_evaluation.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def run_evaluation():
    dataset = load_eval_data()
    
    # 1. Evaluate Legacy Matcher
    legacy_results = defaultdict(lambda: {"true_positives": 0, "false_positives": 0, "false_negatives": 0, "latency": []})
    
    # Map Z901 -> 'פחד נטישה' for legacy comparison
    id_to_legacy = {"Z901": "פחד נטישה", "Z902": "הזדהות השלכתית"}
    
    from retrieval import find_entry_concepts
    
    for item in dataset:
        text = item["text"]
        expected_ids = item["expected_matches"]
        category = item["category"]
        
        expected_legacy = [id_to_legacy[x] for x in expected_ids]
        
        start = time.perf_counter()
        found_legacy = find_entry_concepts(text, legacy_gen)
        latency = time.perf_counter() - start
        
        legacy_results[category]["latency"].append(latency)
        
        # Calculate precision/recall components
        found_set = set(found_legacy)
        expected_set = set(expected_legacy)
        
        legacy_results[category]["true_positives"] += len(found_set & expected_set)
        legacy_results[category]["false_positives"] += len(found_set - expected_set)
        legacy_results[category]["false_negatives"] += len(expected_set - found_set)

    # 2. Evaluate Trie Matcher
    trie_results = defaultdict(lambda: {"true_positives": 0, "false_positives": 0, "false_negatives": 0, "latency": []})
    
    for item in dataset:
        text = item["text"]
        expected_ids = item["expected_matches"]
        category = item["category"]
        
        start = time.perf_counter()
        found_trie = trie_matcher.find(text)
        latency = time.perf_counter() - start
        
        trie_results[category]["latency"].append(latency)
        
        found_ids = [m.card_id for m in found_trie]
        
        found_set = set(found_ids)
        expected_set = set(expected_ids)
        
        trie_results[category]["true_positives"] += len(found_set & expected_set)
        trie_results[category]["false_positives"] += len(found_set - expected_set)
        trie_results[category]["false_negatives"] += len(expected_set - found_set)

    # Compile report
    report = {
        "legacy_metrics": {},
        "trie_metrics": {}
    }
    
    def compile_metrics(results_dict, report_dict):
        for cat, stats in results_dict.items():
            tp = stats["true_positives"]
            fp = stats["false_positives"]
            fn = stats["false_negatives"]
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            
            latencies = stats["latency"]
            latencies.sort()
            p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
            mean_lat = sum(latencies)/len(latencies) if latencies else 0
            
            report_dict[cat] = {
                "precision": precision,
                "recall": recall,
                "p95_latency_ms": p95 * 1000,
                "mean_latency_ms": mean_lat * 1000
            }
            
    compile_metrics(legacy_results, report["legacy_metrics"])
    compile_metrics(trie_results, report["trie_metrics"])
    
    import os
    os.makedirs("out", exist_ok=True)
    with open("out/evaluation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    run_evaluation()
