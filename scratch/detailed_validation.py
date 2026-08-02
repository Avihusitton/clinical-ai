import json
import re

def inspect_glossary_details():
    with open("data/glossary.json", "r", encoding="utf-8") as f:
        glossary_data = json.load(f)
    
    concepts = glossary_data.get("concepts", {})
    print(f"Total concepts in data/glossary.json: {len(concepts)}")
    
    # Check fields present across concepts
    all_fields = set()
    for term, details in concepts.items():
        all_fields.update(details.keys())
    print("All concept fields found in data/glossary.json:", sorted(list(all_fields)))

    # Inspect parent terms and check if targets exist
    all_terms = set(concepts.keys())
    parents = {}
    for term, details in concepts.items():
        p = details.get("parent")
        if p:
            parents[term] = p
            
    print(f"Total concepts with parent specified: {len(parents)}")
    broken_parents = []
    for term, p in parents.items():
        if p not in all_terms:
            broken_parents.append((term, p))
    print(f"Broken parent targets: {broken_parents}")

    # Inspect official glossary
    off_entries = []
    with open("data/official_glossary/official_glossary.sample.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                off_entries.append(json.loads(line))
                
    print(f"\nOfficial Glossary entries count: {len(off_entries)}")
    for e in off_entries:
        print(e)

if __name__ == "__main__":
    inspect_glossary_details()
