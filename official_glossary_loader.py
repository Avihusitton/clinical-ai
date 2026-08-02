import json
import hashlib
from typing import List, Dict, Any

class OfficialGlossaryLoader:
    def _get_driver(self):
                return GraphDatabase
    def __init__(self, store, neo4j_driver):
        self.store = store
        self.driver = neo4j_driver

    HASH_EXCLUDED_FIELDS = {"card_hash", "created_at", "updated_at", "dictionary_version"}

    def _hash_record(self, record: Dict[str, Any]) -> str:
        # Create a stable hash representing the content, excluding volatile metadata
        filtered_record = {k: v for k, v in record.items() if k not in self.HASH_EXCLUDED_FIELDS}
        content = json.dumps(filtered_record, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def validate(self) -> List[str]:
        # Returns errors
        return self.store.validate()

    def _get_existing_shadows(self, pilot_id: str) -> Dict[str, str]:
        # Returns Dict[card_id] = card_hash
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n:OfficialEntryShadow {pilot_id: $pilot_id}) RETURN n.card_id AS card_id, n.card_hash AS card_hash",
                pilot_id=pilot_id
            )
            return {record["card_id"]: record["card_hash"] for record in result}

    def _get_legacy_mappings(self, canonical_name: str, aliases: List[str]) -> Dict[str, Any]:
        with self.driver.session() as session:
            # Check for exact canonical match on Concept
            res = session.run("MATCH (c:Concept) WHERE c.canonical_name = $name RETURN c.canonical_name AS name LIMIT 1", name=canonical_name).single()
            if res:
                return {"type": "exact_concept", "name": res["name"]}
                
            # Check for exact alias match on Concept (assuming Concept has aliases property, or we just check canonical)
            for alias in aliases:
                res = session.run("MATCH (c:Concept) WHERE c.canonical_name = $alias RETURN c.canonical_name AS name LIMIT 1", alias=alias).single()
                if res:
                    return {"type": "alias_concept", "name": res["name"]}
                    
            # Check for Exercise match
            res = session.run("MATCH (e:Exercise) WHERE e.name = $name RETURN e.name AS name LIMIT 1", name=canonical_name).single()
            if res:
                return {"type": "exact_exercise", "name": res["name"]}
                
        return None

    def dry_run(self, pilot_id: str) -> Dict[str, Any]:
        report = {
            "new_entries": 0,
            "updated_entries": 0,
            "unchanged_entries": 0,
            "duplicate_card_ids": 0,
            "alias_collisions": len(self.store.get_alias_collisions()),
            "unresolved_targets": 0,
            "self_links": 0,
            "invalid_types": 0,
            "invalid_certainty": 0,
            "exact_legacy_concept_mappings": 0,
            "alias_legacy_concept_mappings": 0,
            "exact_legacy_exercise_mappings": 0,
            "ambiguous_legacy_mappings": 0,
            "unmapped_official_entries": 0
        }
        
        errors = self.validate()
        report["duplicate_card_ids"] = len([e for e in errors if "Duplicate" in e])
        
        existing = self._get_existing_shadows(pilot_id)
        
        all_ids = set([entry["card_id"] for entry in self.store.get_all_entries()])

        for entry in self.store.get_all_entries():
            card_id = entry["card_id"]
            card_hash = self._hash_record(entry)
            
            if card_id in existing:
                if existing[card_id] == card_hash:
                    report["unchanged_entries"] += 1
                else:
                    report["updated_entries"] += 1
            else:
                report["new_entries"] += 1
                
            entry_type = entry.get("entry_type")
            canonical_name = entry.get("entry_name", "")
            aliases = entry.get("aliases_and_spellings", [])
            
            mapping = self._get_legacy_mappings(canonical_name, aliases)
            if mapping:
                if mapping["type"] == "exact_concept":
                    report["exact_legacy_concept_mappings"] += 1
                elif mapping["type"] == "alias_concept":
                    report["alias_legacy_concept_mappings"] += 1
                elif mapping["type"] == "exact_exercise":
                    report["exact_legacy_exercise_mappings"] += 1
            else:
                report["unmapped_official_entries"] += 1
                
            # Check relationships for unresolved targets
            relations = ["parent_terms", "child_terms", "parallel_terms", "distinguish_from"]
            for rel in relations:
                for target in entry.get(rel, []):
                    if not self.store.get_by_card_id(target):
                        report["unresolved_targets"] += 1
                    if target == card_id:
                        report["self_links"] += 1
                        
        return report

    def export_plan(self, pilot_id: str) -> List[Dict[str, Any]]:
        plan = []
        for entry in self.store.get_all_entries():
            card_id = entry["card_id"]
            card_hash = self._hash_record(entry)
            
            params = {
                "pilot_id": pilot_id,
                "card_id": card_id,
                "card_hash": card_hash,
                "entry_name": entry.get("entry_name", ""),
                "entry_type": entry.get("entry_type", ""),
                "status": entry.get("status", "")
            }
            query = """
            MERGE (n:OfficialEntryShadow {card_id: $card_id, pilot_id: $pilot_id})
            SET n += {
                card_hash: $card_hash,
                entry_name: $entry_name,
                entry_type: $entry_type,
                status: $status
            }
            """
            plan.append({"query": query, "params": params})
            
            for alias in entry.get("aliases_and_spellings", []):
                alias_params = {
                    "pilot_id": pilot_id,
                    "card_id": card_id,
                    "alias": alias
                }
                alias_query = """
                MATCH (n:OfficialEntryShadow {card_id: $card_id, pilot_id: $pilot_id})
                MERGE (a:OfficialAliasShadow {alias: $alias, pilot_id: $pilot_id})
                MERGE (a)-[:ALIAS_OF]->(n)
                """
                plan.append({"query": alias_query, "params": alias_params})
        return plan

    def load_shadow(self, pilot_id: str):
        plan = self.export_plan(pilot_id)
        with self.driver.session() as session:
            for item in plan:
                session.run(item["query"], **item["params"])
