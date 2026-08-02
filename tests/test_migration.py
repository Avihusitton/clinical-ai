import json
import pytest

MIGRATION_FIELDS = [
    "card_id",
    "parent_terms",
    "child_terms",
    "parallel_terms",
    "distinguish_from",
    "see_also",
    "related_techniques",
    "related_exercises"
]

def migrate_identifiers_in_record(record: dict) -> dict:
    """
    Safely migrates T-series identifiers (e.g., 'T001') to Z-series ('Z901')
    only within specific allowed fields to prevent corrupting timestamps, prose, hashes, etc.
    """
    out = record.copy()
    
    def replace_id(val):
        if isinstance(val, str) and val.startswith("T00"):
            return val.replace("T00", "Z90")
        if isinstance(val, str) and val.startswith("T0"):
            return val.replace("T0", "Z9")
        if isinstance(val, str) and val.startswith("T"):
            # Ensure it's T followed by numbers
            if len(val) > 1 and val[1:].isdigit():
                return val.replace("T", "Z9")
        return val

    for field in MIGRATION_FIELDS:
        if field in out:
            val = out[field]
            if isinstance(val, str):
                out[field] = replace_id(val)
            elif isinstance(val, list):
                out[field] = [replace_id(item) for item in val]
                
    return out

def test_migration_preserves_unrelated_fields():
    original = {
        "card_id": "T001",
        "entry_name": "T001 is a great concept",
        "updated_at": "2023-01-01T00:00:00Z",
        "parent_terms": ["T002", "T003"],
        "card_hash": "T001HASH"
    }
    
    migrated = migrate_identifiers_in_record(original)
    
    assert migrated["card_id"] == "Z901"
    assert migrated["entry_name"] == "T001 is a great concept", "Prose must not be modified"
    assert migrated["updated_at"] == "2023-01-01T00:00:00Z", "Timestamps must not be modified"
    assert migrated["parent_terms"] == ["Z902", "Z903"], "List identifiers must be modified"
    assert migrated["card_hash"] == "T001HASH", "Hashes must not be modified"
