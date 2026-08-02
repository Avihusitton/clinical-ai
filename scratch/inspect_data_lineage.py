import os
import json

def read_file(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    return ""

print("=== handoff_dictionary_integration/DATA_LINEAGE.md ===")
print(read_file("handoff_dictionary_integration/DATA_LINEAGE.md")[:2000])

print("\n=== handoff_dictionary_integration/FILES_FOR_REVIEW.md ===")
print(read_file("handoff_dictionary_integration/FILES_FOR_REVIEW.md")[:2000])

print("\n=== handoff_dictionary_integration/SCHEMAS.md ===")
print(read_file("handoff_dictionary_integration/SCHEMAS.md")[:2000])

print("\n=== official_glossary_loader.py ===")
print(read_file("official_glossary_loader.py")[:2000])

print("\n=== official_glossary_store.py ===")
print(read_file("official_glossary_store.py")[:2000])

print("\n=== config.py ===")
print(read_file("config.py")[:2000])
