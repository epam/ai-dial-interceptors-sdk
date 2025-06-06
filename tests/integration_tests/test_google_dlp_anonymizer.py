from dataclasses import dataclass
from typing import Dict, List

import pytest

from aidial_interceptors_sdk.examples.chat_completion.anonymizer.base import (
    Anonymizer,
)
from aidial_interceptors_sdk.examples.chat_completion.google_dlp_anonymiser.anonymizer import (
    GoogleDLPAnonymizer,
)
from aidial_interceptors_sdk.examples.chat_completion.google_dlp_anonymiser.config import (
    DeIdentificationConfig,
)
from aidial_interceptors_sdk.utils._env import get_env


@dataclass
class TestCase:
    __test__ = False

    original_text: str
    anonymized_text: str
    replacements: Dict[str, str]


test_cases: List[TestCase] = [
    TestCase(
        "My name is Adam. Paul is your name. My friend's name is Paul too. My lastname is Smith",
        "My name is [FIRST_NAME-1]. [FIRST_NAME-2] is your name. My friend's name is [FIRST_NAME-2] too. My lastname is [LAST_NAME-1]",
        {
            "Adam": "[FIRST_NAME-1]",
            "Paul": "[FIRST_NAME-2]",
            "Smith": "[LAST_NAME-1]",
        },
    ),
]


@pytest.fixture
def anonymizer():
    return GoogleDLPAnonymizer(
        get_env("GCP_PROJECT_ID"),
        DeIdentificationConfig(info_types=["FIRST_NAME", "LAST_NAME"]),
    )


@pytest.mark.parametrize("test_case", test_cases)
def test_anonymize_deanonymize(test_case: TestCase, anonymizer: Anonymizer):
    text = test_case.original_text
    expected_replacements = test_case.replacements
    expected_anonymized = test_case.anonymized_text

    anon = anonymizer.collect_replacements(text)
    anonymized = anon.anonymize(text)
    assert expected_anonymized == anonymized

    deanonymized = anon.deanonymize(anonymized)

    assert anon.replacements == expected_replacements

    for key in anon.replacements:
        assert key not in anonymized
        assert key in text
        assert key in deanonymized

    assert text == deanonymized


@pytest.mark.parametrize("test_case", test_cases)
def test_anonymize_idempotent(test_case: TestCase, anonymizer: Anonymizer):
    text = test_case.original_text

    anon = anonymizer.collect_replacements(text)
    anonymized1 = anon.anonymize(text)
    anonymized2 = anon.anonymize(anonymized1)

    assert test_case.anonymized_text == anonymized2
    assert anonymized1 == anonymized2
