import re

class LanguagePolicy:
    """
    Ensures that language avoids authoritative statements and uses possibility-oriented language.
    """
    def __init__(self):
        self.possibility_replacements = {
            r"\bis\b": "might be",
            r"\bare\b": "could be",
            r"\bwill\b": "may",
            r"\bmust\b": "might consider",
            r"\bdefinitely\b": "possibly",
            r"\bcertainly\b": "potentially",
            r"\bproves\b": "suggests",
            r"\bshows\b": "indicates",
            r"\bcauses\b": "may contribute to"
        }

    def enforce_possibility_language(self, text: str) -> str:
        """
        A naive deterministic replacement to enforce non-authoritative language.
        Pure-Python, no LLMs.
        """
        modified_text = text
        for auth_word, replacement in self.possibility_replacements.items():
            # Using negative lookbehind/lookahead could improve this, but word boundaries suffice for the spec
            modified_text = re.sub(auth_word, replacement, modified_text, flags=re.IGNORECASE)
        return modified_text

    def review_clinical_possibility(self, possibility: str) -> str:
        return self.enforce_possibility_language(possibility)
