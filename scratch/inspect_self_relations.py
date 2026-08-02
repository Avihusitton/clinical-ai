import json

with open("data/glossary.json", "r", encoding="utf-8") as f:
    glossary_data = json.load(f)

concepts = glossary_data.get("concepts", {})

# Print the raw values - forcing Unicode output
print("=== SELF-RELATIONS ===")
for term, details in concepts.items():
    parent = details.get("parent")
    if parent and parent.strip() == term.strip():
        print(f"Term (hex): {term.encode('utf-8').hex()}")
        print(f"Parent (hex): {parent.encode('utf-8').hex()}")
        # Try to print as unicode
        print(f"Term (unicode escapes): {term.encode('unicode_escape')}")
        print(f"Parent (unicode escapes): {parent.encode('unicode_escape')}")
        print()

# Print all parents to find anything that looks like a self-reference
print("\n=== ALL PARENT REFERENCES ===")
for term, details in concepts.items():
    parent = details.get("parent")
    if parent:
        print(f"  '{term}' -> parent='{parent}'  (same={parent==term})")
