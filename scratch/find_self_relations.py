import json

with open("data/glossary.json", "r", encoding="utf-8") as f:
    glossary_data = json.load(f)

concepts = glossary_data.get("concepts", {})

# Find self-relations
print("=== SELF-RELATIONS (parent == term) ===")
for term, details in concepts.items():
    parent = details.get("parent")
    if parent and parent.strip() == term.strip():
        print(f"  Term: '{term}'")
        print(f"  Parent: '{parent}'")
        print(f"  Same? {parent.strip() == term.strip()}")
        print(f"  term repr: {repr(term)}")
        print(f"  parent repr: {repr(parent)}")
        print()
