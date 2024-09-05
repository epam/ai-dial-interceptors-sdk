from typing import Dict, List, Tuple

import pytest

from aidial_interceptors_sdk.examples.chat_completion.pii_anonymiser.spacy_anonymizer import (
    SpacyAnonymizer,
)

Replacements = Dict[str, str]
TestCase = Tuple[str, Replacements]

test_cases: List[TestCase] = [
    (
        "My name is Adam. Paul is your name. My friend's name is Paul too.",
        {"Adam": "[PERSON-1]", "Paul": "[PERSON-2]"},
    ),
    (
        "London is a capital of the United Kingdom",
        {"London": "[GPE-1]", "the United Kingdom": "[GPE-2]"},
    ),
    (
        "Landon is a capital of the Younited Kingdom",
        {"Landon": "[ORG-1]", "the Younited Kingdom": "[GPE-1]"},
    ),
    (
        "The iPhone is a smartphone made by Apple",
        {"iPhone": "[ORG-1]", "Apple": "[ORG-2]"},
    ),
]


@pytest.mark.parametrize("test_case", test_cases)
def test_anonymize_deanonymize(test_case: TestCase):
    text = test_case[0]
    expected_replacements = test_case[1]

    anon = SpacyAnonymizer()
    anonymized = anon.anonymize(text)
    deanonymized = anon.deanonymize(anonymized)

    assert anon.replacements == expected_replacements

    for key in anon.replacements:
        assert key not in anonymized
        assert key in text
        assert key in deanonymized

    assert text == deanonymized


@pytest.mark.parametrize("test_case", test_cases)
def test_anonymize_idempotent(test_case: TestCase):
    text = test_case[0]

    anon = SpacyAnonymizer()
    anonymized1 = anon.anonymize(text)
    anonymized2 = anon.anonymize(anonymized1)

    assert anonymized1 == anonymized2
