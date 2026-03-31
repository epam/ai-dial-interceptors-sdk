from dataclasses import dataclass

import pytest

from aidial_interceptors_sdk.examples.chat_completion.anonymizer.replacement import (
    create_indexed_replacements,
    parse_anonymized_string,
)
from aidial_interceptors_sdk.examples.chat_completion.anonymizer.replacements import (
    Replacements,
)


@dataclass
class AnonTestCase:
    __test__ = False
    entities: list[str]
    input: str
    expected: list[str | int]


@pytest.mark.parametrize(
    "test",
    [
        AnonTestCase(
            ["FIRST_NAME", "LAST_NAME"],
            "My name is [FIRST_NAME] [LAST_NAME]",
            ["My name is ", 0, " ", 1],
        ),
        AnonTestCase(
            ["FIRST_NAME", "LAST_NAME"],
            "My name is [FIRST_NAME] [LAST_NAME] [[LAST_NAME]] [[FIRST_NAME]]",
            ["My name is ", 0, " ", 1, " [", 1, "] [", 0, "]"],
        ),
    ],
)
def test_parse_anonymized_string(test: AnonTestCase):
    assert parse_anonymized_string(test.entities, test.input) == test.expected


@dataclass
class ReplTestCase:
    __test__ = False
    entities: list[str]
    original: str
    anonymized: str
    expected: dict[str, str] | None


@pytest.mark.parametrize(
    "test",
    [
        ReplTestCase(
            ["FIRST_NAME", "LAST_NAME"],
            "My name is John Smith",
            "My name is [FIRST_NAME] [LAST_NAME]",
            (
                {
                    "John": "[FIRST_NAME-1]",
                    "Smith": "[LAST_NAME-1]",
                }
            ),
        ),
        ReplTestCase(
            ["FIRST_NAME", "LAST_NAME"],
            "My name is John Smith or [Brown] [Peter]",
            "My name is [FIRST_NAME] [LAST_NAME] or [[LAST_NAME]] [[FIRST_NAME]]",
            (
                {
                    "John": "[FIRST_NAME-1]",
                    "Smith": "[LAST_NAME-1]",
                    "Brown": "[LAST_NAME-2]",
                    "Peter": "[FIRST_NAME-2]",
                }
            ),
        ),
    ],
)
def test_create_indexed_replacements(test: ReplTestCase):
    res = create_indexed_replacements(
        Replacements(), test.entities, test.original, test.anonymized
    )
    if res is None:
        assert test.expected is None
    else:
        assert res.replacements == test.expected
