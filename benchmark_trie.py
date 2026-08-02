import time
import json
import tracemalloc
from official_glossary_store import OfficialGlossaryStore
from glossary_alias_index import TrieAliasMatcher
from config import Config
from ingestion_pipeline import CandidateGenerator

def generate_variants(base: str) -> list[str]:
    # Simple variant generator for benchmark
    return [base, f"ב{base}", f"ל{base}", f"ה{base}", f"מ{base}", f"ו{base}", f"ש{base}"]

def generate_mock_data():
    records = []
    # Generate 100 glossary entries and 500 aliases
    for i in range(100):
        aliases = []
        for j in range(5):
            aliases.extend(generate_variants(f"מושג_{i}_{j}"))
        record = {
            "card_id": f"A{i:03d}",
            "canonical_name": f"מושג_ראשי_{i}",
            "entry_name": f"מושג_ראשי_{i}",
            "aliases_and_spellings": aliases,
            "status": "APPROVED",
            "entry_type": "CONCEPT"
        }
        records.append(record)
    return records

def benchmark():
    records = generate_mock_data()
    
    # 1. Benchmark Trie Build Time
    start = time.perf_counter()
    tracemalloc.start()
    trie_matcher = TrieAliasMatcher()
    trie_matcher.build(records)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    trie_build_time = time.perf_counter() - start
    trie_mem_usage = peak / 1024 / 1024 # MB
    
    # Text to match
    text = "המטופל דיווח על מושג_ראשי_50 וגם על במושג_20_1. בנוסף, מושג_ראשי_10 היה רלוונטי."
    
    # 2. Benchmark Trie Latency
    times = []
    for _ in range(1000):
        start = time.perf_counter()
        trie_matcher.find(text)
        times.append(time.perf_counter() - start)
    
    trie_mean = sum(times) / len(times)
    times.sort()
    trie_p95 = times[int(len(times) * 0.95)]
    
    # 3. Benchmark Legacy (Approximation for context)
    class LegacyConfig:
        pass
    
    class MockGenerator:
        def __init__(self, records):
            self.concepts = {r["canonical_name"]: r for r in records}
    
    # Legacy would be scanning text for each concept
    times_legacy = []
    for _ in range(1000):
        start = time.perf_counter()
        found = []
        for r in records:
            if r["canonical_name"] in text:
                found.append(r["canonical_name"])
            for alias in r["aliases_and_spellings"]:
                if alias in text:
                    found.append(alias)
        times_legacy.append(time.perf_counter() - start)
        
    leg_mean = sum(times_legacy) / len(times_legacy)
    times_legacy.sort()
    leg_p95 = times_legacy[int(len(times_legacy) * 0.95)]

    results = {
        "index_build_time": trie_build_time,
        "memory_usage_mb": trie_mem_usage,
        "trie_mean_latency_ms": trie_mean * 1000,
        "trie_p95_latency_ms": trie_p95 * 1000,
        "legacy_mean_latency_ms": leg_mean * 1000,
        "legacy_p95_latency_ms": leg_p95 * 1000,
        "alias_count": sum(len(r["aliases_and_spellings"]) for r in records),
        "glossary_count": len(records)
    }
    
    with open("out/trie_benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    benchmark()
