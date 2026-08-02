import os
import json
import re
import hashlib

def find_validation_errors():
    """Find the exact 2 validation errors"""
    with open("data/glossary.json", "r", encoding="utf-8") as f:
        glossary_data = json.load(f)

    concepts = glossary_data.get("concepts", {})
    
    email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    phone_regex = re.compile(r'\b(?:\+?972[-_ ]?|0)(?:[23489]|5[0-9])[-_ ]?\d{3}[-_ ]?\d{4}\b')
    id_num_regex = re.compile(r'\b\d{9}\b')

    errors = []
    for term, details in concepts.items():
        defn = details.get("definition", "").strip()
        synonyms = details.get("synonyms", [])
        parent = details.get("parent")

        if not term.strip() or not defn:
            errors.append(f"EMPTY_FIELD: term='{term}', def_empty={not defn}")

        combined = f"{term} {defn} {' '.join(synonyms)}"
        if email_regex.search(combined):
            errors.append(f"EMAIL: term='{term}'")
        if phone_regex.search(combined):
            errors.append(f"PHONE: term='{term}'")
        if id_num_regex.search(combined):
            errors.append(f"ID_NUM: term='{term}'")

    print(f"Dictionary errors: {errors}")

    # Also check official glossary
    off_entries = []
    with open("data/official_glossary/official_glossary.sample.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                off_entries.append(json.loads(line.strip()))

    for entry in off_entries:
        card_id = entry.get("card_id", "").strip()
        cname = entry.get("canonical_name", "").strip()
        defn = entry.get("definition", "").strip()
        aliases = entry.get("aliases", [])

        if not card_id or not cname or not defn:
            errors.append(f"GLOSSARY EMPTY_FIELD: card={card_id}")
        combined = f"{card_id} {cname} {defn} {' '.join(aliases)}"
        if email_regex.search(combined):
            errors.append(f"GLOSSARY EMAIL: card={card_id}")
        if id_num_regex.search(combined):
            errors.append(f"GLOSSARY ID_NUM: card={card_id}")

    print(f"All errors found: {errors}")

    # Check UTF-8 for all terms
    for term, details in concepts.items():
        defn = details.get("definition", "").strip()
        try:
            term.encode('utf-8').decode('utf-8')
        except Exception as e:
            errors.append(f"UTF8_TERM: '{term}': {e}")
        try:
            defn.encode('utf-8').decode('utf-8')
        except Exception as e:
            errors.append(f"UTF8_DEF: term='{term}': {e}")

    print(f"After UTF-8 check, errors: {errors}")

    # Check if there are any 9-digit sequences in terms or defs
    for term, details in concepts.items():
        defn = details.get("definition", "").strip()
        synonyms = details.get("synonyms", [])
        combined = f"{term} {defn} {' '.join(synonyms)}"
        m = id_num_regex.findall(combined)
        if m:
            print(f"ID_NUM hit in '{term}': {m}")

if __name__ == "__main__":
    find_validation_errors()
