import re
from typing import Protocol, List, Dict, Any
from dataclasses import dataclass

@dataclass(frozen=True)
class GlossaryMatch:
    card_id: str
    canonical_name: str
    matched_form: str
    normalized_form: str
    start: int
    end: int
    match_method: str
    priority: int
    alias_type: str

class AliasMatcher(Protocol):
    def build(self, records: List[Dict[str, Any]]) -> None:
        ...

    def find(self, text: str) -> List[GlossaryMatch]:
        ...

class TrieNode:
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.matches: List[Dict[str, Any]] = []

class TrieAliasMatcher:
    def __init__(self):
        self.root = TrieNode()

    def _normalize(self, text: str) -> str:
        # Basic normalization for pilot: remove niqqud, lowercase, strip
        text = re.sub(r'[\u0591-\u05C7]', '', text)
        return text.strip()

    def build(self, records: List[Dict[str, Any]]) -> None:
        for record in records:
            card_id = record["card_id"]
            canonical = record["canonical_name"]
            
            # Index canonical name
            self._add_term(canonical, card_id, canonical, "canonical")
            
            # Index aliases
            for alias in record.get("aliases", []):
                self._add_term(alias, card_id, canonical, "alias")

    def _add_term(self, term: str, card_id: str, canonical_name: str, alias_type: str):
        normalized = self._normalize(term)
        if not normalized:
            return
            
        node = self.root
        for char in normalized:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            
        node.matches.append({
            "card_id": card_id,
            "canonical_name": canonical_name,
            "alias_type": alias_type,
            "normalized_form": normalized,
            "original_form": term
        })

    def find(self, text: str) -> List[GlossaryMatch]:
        norm_text = self._normalize(text)
        results = []
        n = len(norm_text)
        
        i = 0
        while i < n:
            node = self.root
            j = i
            longest_match = None
            longest_match_end = -1
            
            while j < n and norm_text[j] in node.children:
                node = node.children[norm_text[j]]
                if node.matches:
                    longest_match = node.matches
                    longest_match_end = j
                j += 1
                
            if longest_match:
                # We found a match ending at longest_match_end
                for match_info in longest_match:
                    results.append(GlossaryMatch(
                        card_id=match_info["card_id"],
                        canonical_name=match_info["canonical_name"],
                        matched_form=match_info["original_form"],
                        normalized_form=match_info["normalized_form"],
                        start=i,
                        end=longest_match_end + 1,
                        match_method="trie",
                        priority=1 if match_info["alias_type"] == "canonical" else 2,
                        alias_type=match_info["alias_type"]
                    ))
                i = longest_match_end + 1
            else:
                i += 1
                
        return results
