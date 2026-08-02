"""
Detailed preflight — find the exact source of the 2 validation errors
reported in run_preflight_checks.py
"""
import json
import re

def run_preflight_verbose():
    with open("data/glossary.json", "r", encoding="utf-8") as f:
        glossary_data = json.load(f)

    concepts = glossary_data.get("concepts", {})

    email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    phone_regex = re.compile(r'\b(?:\+?972[-_ ]?|0)(?:[23489]|5[0-9])[-_ ]?\d{3}[-_ ]?\d{4}\b')
    id_num_regex = re.compile(r'\b\d{9}\b')

    concept_count = len(concepts)
    glossary_entry_count = 0
    alias_count = 0
    relationship_count = 0
    duplicate_id_count = 0
    empty_required_field_count = 0
    broken_relationship_count = 0
    orphan_concept_count = 0
    potential_identifier_count = 0
    validation_error_count = 0
    validation_warning_count = 0

    concept_ids = set()
    preferred_terms = set()
    child_map = {term: set() for term in concepts.keys()}

    idx = 1
    for term, details in concepts.items():
        cid = f"CONCEPT-{idx:03d}"
        idx += 1

        pref_term = term.strip()
        defn = details.get("definition", "").strip()
        synonyms = details.get("synonyms", [])
        parent = details.get("parent")
        category = details.get("type", "concept")
        status = details.get("status", "ACTIVE")

        alias_count += len(synonyms)

        # UTF-8
        try:
            term.encode('utf-8').decode('utf-8')
            defn.encode('utf-8').decode('utf-8')
        except Exception as e:
            validation_error_count += 1
            print(f"UTF8 ERROR: {term}: {e}")

        # Dup concept ID
        if cid in concept_ids:
            duplicate_id_count += 1
            validation_error_count += 1
            print(f"DUP ID: {cid}")
        concept_ids.add(cid)

        if pref_term in preferred_terms:
            validation_warning_count += 1
            print(f"DUP TERM: {pref_term}")
        preferred_terms.add(pref_term)

        # Empty required fields
        if not pref_term or not defn:
            empty_required_field_count += 1
            validation_error_count += 1
            print(f"EMPTY FIELD: term='{pref_term}' def='{defn}'")

        # Relationship target
        if parent:
            parent = parent.strip()
            relationship_count += 1
            if parent == pref_term:
                validation_error_count += 1
                print(f"SELF-RELATION: {pref_term}")
            if parent not in concepts:
                broken_relationship_count += 1
                validation_error_count += 1
                print(f"BROKEN REL: {pref_term} -> {parent}")
            else:
                child_map[parent].add(pref_term)

        # PII
        combined_text = f"{pref_term} {defn} {' '.join(synonyms)}"
        if email_regex.search(combined_text):
            potential_identifier_count += 1
            validation_error_count += 1
            print(f"EMAIL FOUND: {pref_term}: {email_regex.findall(combined_text)}")
        if phone_regex.search(combined_text):
            potential_identifier_count += 1
            validation_error_count += 1
            print(f"PHONE FOUND: {pref_term}: {phone_regex.findall(combined_text)}")
        if id_num_regex.search(combined_text):
            potential_identifier_count += 1
            validation_error_count += 1
            print(f"9-DIGIT ID FOUND: {pref_term}: {id_num_regex.findall(combined_text)}")

    # Orphan concepts
    for term in concepts:
        p = concepts[term].get("parent")
        children = child_map[term]
        if not p and len(children) == 0:
            orphan_concept_count += 1

    # Official glossary
    off_entries = []
    with open("data/official_glossary/official_glossary.sample.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entry = json.loads(line.strip())
                off_entries.append(entry)
                glossary_entry_count += 1

                card_id = entry.get("card_id", "").strip()
                cname = entry.get("canonical_name", "").strip()
                defn = entry.get("definition", "").strip()
                aliases = entry.get("aliases", [])
                alias_count += len(aliases)

                if not card_id or not cname or not defn:
                    empty_required_field_count += 1
                    validation_error_count += 1
                    print(f"GLOSSARY EMPTY: card={card_id}")

                combined = f"{card_id} {cname} {defn} {' '.join(aliases)}"
                if email_regex.search(combined):
                    potential_identifier_count += 1
                    validation_error_count += 1
                    print(f"GLOSSARY EMAIL: {card_id}")
                if phone_regex.search(combined):
                    potential_identifier_count += 1
                    validation_error_count += 1
                    print(f"GLOSSARY PHONE: {card_id}")
                if id_num_regex.search(combined):
                    potential_identifier_count += 1
                    validation_error_count += 1
                    print(f"GLOSSARY ID_NUM: {card_id}")

    print("\n=== FINAL REPORT ===")
    print(f"concept_count: {concept_count}")
    print(f"glossary_entry_count: {glossary_entry_count}")
    print(f"alias_count: {alias_count}")
    print(f"relationship_count: {relationship_count}")
    print(f"duplicate_id_count: {duplicate_id_count}")
    print(f"empty_required_field_count: {empty_required_field_count}")
    print(f"broken_relationship_count: {broken_relationship_count}")
    print(f"orphan_concept_count: {orphan_concept_count}")
    print(f"potential_identifier_count: {potential_identifier_count}")
    print(f"validation_error_count: {validation_error_count}")
    print(f"validation_warning_count: {validation_warning_count}")

if __name__ == "__main__":
    run_preflight_verbose()
