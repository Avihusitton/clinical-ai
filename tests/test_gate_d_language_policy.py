import pytest
from models.gate_d import LanguagePolicy

def test_language_policy_initialization():
    policy = LanguagePolicy()
    assert policy is not None
