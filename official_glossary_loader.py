import json
import hashlib
from typing import List, Dict, Any

class OfficialGlossaryLoader:
    def __init__(self, store):
        self.store = store

    def _hash_record(self, record: Dict[str, Any]) -> str:
        # Create a stable hash representing the content
        content = json.dumps(record, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def validate(self) -> List[str]:
        errors = []
        card_ids = set()
        for record in self.store.get_all_entries():
            if "card_id" not in record or not record["card_id"]:
                errors.append(f"Missing card_id in record: {record}")
                continue
            if record["card_id"] in card_ids:
                errors.append(f"Duplicate card_id: {record['card_id']}")
            card_ids.add(record["card_id"])
            if "canonical_name" not in record:
                errors.append(f"Missing canonical_name in card {record['card_id']}")
        return errors

    def dry_run(self) -> Dict[str, Any]:
        report = {
            "new_entries": 0,
            "updated_entries": 0,
            "unchanged_entries": 0,
            "duplicate_card_ids": 0,
            "alias_collisions": 0,
            "unresolved_targets": 0,
            "self_links": 0,
            "invalid_types": 0,
            "invalid_certainty": 0
        }
        
        errors = self.validate()
        report["duplicate_card_ids"] = len([e for e in errors if "Duplicate" in e])
        
        # In a full implementation, we'd query Neo4j to see if nodes exist
        # For this pilot scaffold, we assume all are new
        report["new_entries"] = len(self.store.get_all_entries())
        
        return report

    def load_shadow(self):
        # Scaffold: In future, this will connect to Neo4j and MERGE nodes
        pass

    def export_plan(self):
        # Scaffold: Return a plan of Cypher queries
        return []
