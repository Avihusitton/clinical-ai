import json
from pathlib import Path
from typing import Dict, Any, List

class OfficialGlossaryStore:
    def __init__(self, file_path: str = "data/official_glossary/official_glossary.sample.jsonl"):
        self.file_path = Path(file_path)
        self.entries: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if not self.file_path.exists():
            return
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                self.entries[record["card_id"]] = record

    def get_entry(self, card_id: str) -> Dict[str, Any]:
        return self.entries.get(card_id)

    def get_all_entries(self) -> List[Dict[str, Any]]:
        return list(self.entries.values())
