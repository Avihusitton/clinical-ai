import re
import json
from pathlib import Path
from typing import Protocol, List, Dict, Any, Optional
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
    collision_status: str

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
    def __init__(self, exceptions_path: str = "data/official_glossary/alias_exceptions.json"):
        self.root = TrieNode()
        self.exceptions_path = Path(exceptions_path)
        self.allow_short = set()
        self.blocked = set()
        self._load_exceptions()

    def _load_exceptions(self):
        if self.exceptions_path.exists():
            with open(self.exceptions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.allow_short = set(data.get("allow_short", []))
                self.blocked = set(data.get("blocked", []))

    def _is_niqqud(self, char: str) -> bool:
        # Hebrew niqqud range
        return '\u0591' <= char <= '\u05C7'

    def _is_punctuation(self, char: str) -> bool:
        return not char.isalnum()

    def _normalize(self, text: str) -> str:
        # Convert punctuation to spaces, strip niqqud, lower case, collapse spaces
        res = []
        for c in text:
            if self._is_niqqud(c):
                continue
            if self._is_punctuation(c):
                res.append(' ')
            else:
                res.append(c.lower())
        return ' '.join(''.join(res).split())

    def build(self, records: List[Dict[str, Any]]) -> None:
        for record in records:
            card_id = record["card_id"]
            canonical = record.get("entry_name", "")
            
            self._add_term(canonical, card_id, canonical, "canonical")
            for alias in record.get("aliases_and_spellings", []):
                self._add_term(alias, card_id, canonical, "alias")

    def _add_term(self, term: str, card_id: str, canonical_name: str, alias_type: str):
        if not term:
            return
            
        normalized = self._normalize(term)
        if not normalized:
            return
            
        if normalized in self.blocked:
            return
            
        # Block short aliases unless allowed
        if len(normalized) < 3 and normalized not in self.allow_short:
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

    def _create_index_mapping(self, text: str):
        norm_text = ""
        mapping = [] # mapping[norm_index] = original_index
        last_was_space = False
        
        for i, char in enumerate(text):
            if self._is_niqqud(char):
                continue
            
            if self._is_punctuation(char):
                if not last_was_space and len(norm_text) > 0:
                    norm_text += ' '
                    mapping.append(i)
                    last_was_space = True
            else:
                norm_text += char.lower()
                mapping.append(i)
                last_was_space = False
                
        # Trim trailing space
        if norm_text.endswith(' '):
            norm_text = norm_text[:-1]
            mapping.pop()
            
        return norm_text, mapping

    def _is_boundary(self, text: str, index: int) -> bool:
        if index < 0 or index >= len(text):
            return True
        char = text[index]
        return self._is_punctuation(char)

    def find(self, text: str) -> List[GlossaryMatch]:
        norm_text, mapping = self._create_index_mapping(text)
        results: List[GlossaryMatch] = []
        n = len(norm_text)
        
        i = 0
        while i < n:
            # Check word boundary before the match starts
            orig_i = mapping[i]
            if not self._is_boundary(text, orig_i - 1):
                i += 1
                continue
                
            node = self.root
            j = i
            best_valid_matches = None
            best_valid_end = -1
            
            while j < n and norm_text[j] in node.children:
                node = node.children[norm_text[j]]
                # Verify word boundary after the match ends
                if node.matches:
                    orig_j = mapping[j]
                    if self._is_boundary(text, orig_j + 1):
                        best_valid_matches = node.matches
                        best_valid_end = j
                j += 1
                
            if best_valid_matches:
                orig_start = mapping[i]
                orig_end = mapping[best_valid_end] + 1
                matched_str = text[orig_start:orig_end]
                
                # Check for collisions among the longest match
                unique_cards = set([m["card_id"] for m in best_valid_matches])
                collision_status = "COLLISION" if len(unique_cards) > 1 else "RESOLVED"
                
                for match_info in best_valid_matches:
                    results.append(GlossaryMatch(
                        card_id=match_info["card_id"],
                        canonical_name=match_info["canonical_name"],
                        matched_form=matched_str,
                        normalized_form=match_info["normalized_form"],
                        start=orig_start,
                        end=orig_end,
                        match_method="trie",
                        priority=1 if match_info["alias_type"] == "canonical" else 2,
                        alias_type=match_info["alias_type"],
                        collision_status=collision_status
                    ))
                i = best_valid_end + 1
            else:
                i += 1
                
        return results
