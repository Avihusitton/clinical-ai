import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import jsonschema

class OfficialGlossaryStore:
    def __init__(self, file_path: str = "data/official_glossary/official_glossary.sample.jsonl", schema_path: str = "data/official_glossary/schema.json"):
        self.file_path = Path(file_path)
        self.schema_path = Path(schema_path)
        
        with open(self.schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)
            
        self.entries: List[Dict[str, Any]] = []
        self._by_card_id: Dict[str, Dict[str, Any]] = {}
        self._by_canonical: Dict[str, List[str]] = {} # normalized -> [card_id, ...]
        self._by_alias: Dict[str, List[str]] = {} # normalized -> [card_id, ...]
        self.validation_errors: List[str] = []

    def _normalize(self, text: str) -> str:
        if not text:
            return ""
        return text.strip().lower()

    def load(self):
        if not self.file_path.exists():
            return
            
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    card_id = record.get("card_id", f"UNKNOWN_L{line_num}")
                    
                    try:
                        jsonschema.validate(instance=record, schema=self.schema, format_checker=jsonschema.FormatChecker())
                    except jsonschema.exceptions.ValidationError as e:
                        self.validation_errors.append(f"Line {line_num} [Card {card_id}] schema error: {e.message}")
                        continue
                        
                    if card_id in self._by_card_id:
                        self.validation_errors.append(f"Line {line_num} [Card {card_id}] Duplicate card_id. Not overwriting.")
                        continue
                        
                    self.entries.append(record)
                    self._by_card_id[card_id] = record
                    
                    entry_name = record.get("entry_name", "")
                    norm_entry = self._normalize(entry_name)
                    if norm_entry:
                        if norm_entry not in self._by_canonical:
                            self._by_canonical[norm_entry] = []
                        self._by_canonical[norm_entry].append(card_id)
                        
                    aliases = record.get("aliases_and_spellings", [])
                    for alias in aliases:
                        norm_alias = self._normalize(alias)
                        if norm_alias:
                            if norm_alias not in self._by_alias:
                                self._by_alias[norm_alias] = []
                            self._by_alias[norm_alias].append(card_id)

                except json.JSONDecodeError as e:
                    self.validation_errors.append(f"Line {line_num}: JSON decode error: {str(e)}")

    def validate(self) -> List[str]:
        errors = list(self.validation_errors)
        
        # Check duplicate canonical names
        for canonical, ids in self._by_canonical.items():
            if len(ids) > 1:
                errors.append(f"Duplicate normalized entry_name '{canonical}' found in cards: {ids}")
                
        # Check alias collisions (same alias across different cards)
        # It's a collision if multiple distinct cards share the same alias, or if an alias matches another card's canonical name
        for alias, ids in self._by_alias.items():
            unique_ids = set(ids)
            if alias in self._by_canonical:
                unique_ids.update(self._by_canonical[alias])
            if len(unique_ids) > 1:
                errors.append(f"Alias collision for '{alias}' found in cards: {list(unique_ids)}")
                
        return errors

    def get_by_card_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        return self._by_card_id.get(card_id)

    def find_by_canonical_name(self, name: str) -> List[Dict[str, Any]]:
        norm = self._normalize(name)
        card_ids = self._by_canonical.get(norm, [])
        return [self._by_card_id[cid] for cid in card_ids]

    def find_by_alias(self, alias: str) -> List[Dict[str, Any]]:
        norm = self._normalize(alias)
        card_ids = self._by_alias.get(norm, [])
        return [self._by_card_id[cid] for cid in card_ids]

    def get_all_entries(self) -> List[Dict[str, Any]]:
        return list(self.entries)

    def get_alias_collisions(self) -> Dict[str, List[str]]:
        collisions = {}
        for alias, ids in self._by_alias.items():
            unique_ids = set(ids)
            if alias in self._by_canonical:
                unique_ids.update(self._by_canonical[alias])
            if len(unique_ids) > 1:
                collisions[alias] = list(unique_ids)
        return collisions
