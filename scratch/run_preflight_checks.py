import os
import json
import re
import hashlib

def run_preflight():
    # Load dictionary
    with open("data/glossary.json", "r", encoding="utf-8") as f:
        glossary_raw = f.read()
        glossary_data = json.loads(glossary_raw)

    concepts = glossary_data.get("concepts", {})
    
    # Load official glossary
    off_entries = []
    with open("data/official_glossary/official_glossary.sample.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                off_entries.append(json.loads(line.strip()))

    # Regex for PII / clinical identifiers
    email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    phone_regex = re.compile(r'\b(?:\+?972[-_ ]?|0)(?:[23489]|5[0-9])[-_ ]?\d{3}[-_ ]?\d{4}\b')
    id_num_regex = re.compile(r'\b\d{9}\b') # 9-digit Israeli ID
    
    # Tracking counters
    concept_count = len(concepts)
    glossary_entry_count = len(off_entries)
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

    # Validate Concepts
    concept_items = []
    idx = 1
    for term, details in concepts.items():
        # Generate stable ID deterministically from canonical term
        cid = f"CONCEPT-{idx:03d}"
        idx += 1
        
        pref_term = term.strip()
        defn = details.get("definition", "").strip()
        synonyms = details.get("synonyms", [])
        parent = details.get("parent")
        category = details.get("type", "concept")
        status = details.get("status", "ACTIVE")
        source = details.get("source", "data/glossary.json")

        alias_count += len(synonyms)

        # Check UTF-8 validity
        try:
            term.encode('utf-8').decode('utf-8')
            defn.encode('utf-8').decode('utf-8')
        except Exception:
            validation_error_count += 1

        # Check duplicate concept IDs & preferred terms
        if cid in concept_ids:
            duplicate_id_count += 1
            validation_error_count += 1
        concept_ids.add(cid)

        if pref_term in preferred_terms:
            validation_warning_count += 1
        preferred_terms.add(pref_term)

        # Check empty required fields (preferred_term, definition)
        if not pref_term or not defn:
            empty_required_field_count += 1
            validation_error_count += 1

        # Check relationship target (parent)
        if parent:
            parent = parent.strip()
            relationship_count += 1
            if parent == pref_term:
                # Self relation!
                validation_error_count += 1
            if parent not in concepts:
                broken_relationship_count += 1
                validation_error_count += 1
            else:
                child_map[parent].add(pref_term)

        # Check PII
        combined_text = f"{pref_term} {defn} {' '.join(synonyms)}"
        if email_regex.search(combined_text) or phone_regex.search(combined_text) or id_num_regex.search(combined_text):
            potential_identifier_count += 1
            validation_error_count += 1

        concept_items.append({
            "concept_id": cid,
            "preferred_term": pref_term,
            "definition": defn,
            "aliases": synonyms,
            "category": category,
            "status": status,
            "source": source,
            "parent": parent
        })

    # Check orphan concepts (no parent AND no children)
    for term, details in concepts.items():
        p = details.get("parent")
        children = child_map[term]
        if not p and len(children) == 0:
            orphan_concept_count += 1

    # Validate Official Glossary entries
    for entry in off_entries:
        card_id = entry.get("card_id", "").strip()
        cname = entry.get("canonical_name", "").strip()
        defn = entry.get("definition", "").strip()
        aliases = entry.get("aliases", [])
        status = entry.get("status", "APPROVED")

        alias_count += len(aliases)

        if not card_id or not cname or not defn:
            empty_required_field_count += 1
            validation_error_count += 1

        combined_text = f"{card_id} {cname} {defn} {' '.join(aliases)}"
        if email_regex.search(combined_text) or phone_regex.search(combined_text) or id_num_regex.search(combined_text):
            potential_identifier_count += 1
            validation_error_count += 1

    preflight_report = {
        "concept_count": concept_count,
        "glossary_entry_count": glossary_entry_count,
        "alias_count": alias_count,
        "relationship_count": relationship_count,
        "duplicate_id_count": duplicate_id_count,
        "empty_required_field_count": empty_required_field_count,
        "broken_relationship_count": broken_relationship_count,
        "orphan_concept_count": orphan_concept_count,
        "potential_identifier_count": potential_identifier_count,
        "validation_error_count": validation_error_count,
        "validation_warning_count": validation_warning_count
    }

    print(json.dumps(preflight_report, indent=2))
    return preflight_report, concept_items, off_entries

if __name__ == "__main__":
    run_preflight()
