import json

print("=== DATA/GLOSSARY.JSON ===")
with open("data/glossary.json", "r", encoding="utf-8") as f:
    glossary_data = json.load(f)

concepts = glossary_data.get("concepts", {})
print(f"Total concepts in data/glossary.json: {len(concepts)}")
for i, (term, details) in enumerate(list(concepts.items())[:10]):
    print(f"[{i+1}] {term} -> {details}")

print("\n=== DATA/OFFICIAL_GLOSSARY/OFFICIAL_GLOSSARY.SAMPLE.JSONL ===")
glossary_entries = []
with open("data/official_glossary/official_glossary.sample.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            glossary_entries.append(json.loads(line))
print(f"Total entries in official_glossary.sample.jsonl: {len(glossary_entries)}")
for i, entry in enumerate(glossary_entries):
    print(f"[{i+1}] {entry}")
