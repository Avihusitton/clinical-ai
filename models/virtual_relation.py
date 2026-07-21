from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class VirtualRelation:
    source_id: str
    target_id: str
    relation_type: str
    provenance_path: tuple[str, ...]
    score: float
    is_second_order: bool = True
