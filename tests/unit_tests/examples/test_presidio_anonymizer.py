from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional
import importlib

import pytest

from aidial_interceptors_sdk.examples.chat_completion.anonymizer.base import (
    Anonymizer,
)
from aidial_interceptors_sdk.examples.chat_completion.presidio_anonymizer.anonymizer import (
    PresidioAnonymizer,
)

_INPUT_TEXT = ("My name is John. I live in Rome and work at Google. My employee id is GL-456698. In my spare time I play tennis. "
               + "Kate is a friend of mine. She also works at Google, but she lives in Madrid and loves football. "
               + "You can contact me by phone +380956784534 and Kate by katty@gmail.com.")


@dataclass
class TestCase:
    __test__ = False

    original_text: str
    anonymized_text: str
    replacements: Dict[str, str]
    env_vars: Optional[Dict[str, str]]


test_cases: List[TestCase] = [
    TestCase(
        _INPUT_TEXT,

        "My name is [PERSON-1]. I live in [LOCATION-1] and work at Google. My employee id is GL-456698. In my spare time I play tennis. "
        + "[PERSON-2] is a friend of mine. She also works at Google, but she lives in [LOCATION-2] and loves football. "
        + "You can contact me by phone [PHONE_NUMBER-1] and [PERSON-2] by [EMAIL_ADDRESS-1].",

        {
            "John": "[PERSON-1]",
            "Rome": "[LOCATION-1]",
            "Kate": "[PERSON-2]",
            "Madrid": "[LOCATION-2]",
            "+380956784534": "[PHONE_NUMBER-1]",
            "katty@gmail.com": "[EMAIL_ADDRESS-1]",
        },

        env_vars={},
    ),

    TestCase(
        _INPUT_TEXT,

        "My name is [PERSON-1]. I live in Rome and work at Google. My employee id is GL-456698. In my spare time I play tennis. "
        + "[PERSON-2] is a friend of mine. She also works at Google, but she lives in Madrid and loves football. "
        + "You can contact me by phone [PHONE_NUMBER-1] and [PERSON-2] by [EMAIL_ADDRESS-1].",

        {
            "John": "[PERSON-1]",
            "Kate": "[PERSON-2]",
            "+380956784534": "[PHONE_NUMBER-1]",
            "katty@gmail.com": "[EMAIL_ADDRESS-1]",
        },

        env_vars={
            "PRESIDIO_ALLOW_LIST": "Rome, Madrid"
        },
    ),

    TestCase(
        _INPUT_TEXT,

        "My name is John. I live in Rome and work at Google. My employee id is GL-456698. In my spare time I play tennis. "
        + "Kate is a friend of mine. She also works at Google, but she lives in Madrid and loves football. "
        + "You can contact me by phone +380956784534 and Kate by [EMAIL_ADDRESS-1].",

        {
            "katty@gmail.com": "[EMAIL_ADDRESS-1]",
        },

        env_vars={
            "PRESIDIO_CONFIDENCE_SCORE_THRESHOLD": "0.86"
        },
    ),

    TestCase(
        _INPUT_TEXT,

        "My name is [PERSON-1]. I live in [LOCATION-1] and work at Google. My employee id is [EMPLOYEE_ID-1]. In my spare time I play tennis. "
        + "[PERSON-2] is a friend of mine. She also works at Google, but she lives in [LOCATION-2] and loves football. "
        + "You can contact me by phone [PHONE_NUMBER-1] and [PERSON-2] by [EMAIL_ADDRESS-1].",

        {
            "John": "[PERSON-1]",
            "Rome": "[LOCATION-1]",
            "GL-456698": "[EMPLOYEE_ID-1]",
            "Kate": "[PERSON-2]",
            "Madrid": "[LOCATION-2]",
            "+380956784534": "[PHONE_NUMBER-1]",
            "katty@gmail.com": "[EMAIL_ADDRESS-1]",
        },

        env_vars={
            "PRESIDIO_CUSTOM_RECOGNIZERS_CONFIG": """
            - name: "EmployeeIdRecognizer"
              supported_entity: "EMPLOYEE_ID"
              patterns:
                - name: "EmployeeIdRegex"
                  regex: "GL-\\\\d{6}"
                  score: 0.95
              context:
                - "employee"
                - "id"
            """
        },
    ),

    TestCase(
        _INPUT_TEXT,

        "My name is [PERSON-1]. I live in [LOCATION-1] and work at Google. My employee id is GL-456698. In my spare time I play tennis. "
        + "[PERSON-2] is a friend of mine. She also works at Google, but she lives in [LOCATION-2] and loves football. "
        + "You can contact me by phone [PHONE_NUMBER-1] and [PERSON-2] by [EMAIL_ADDRESS-1].",

        {
            "John": "[PERSON-1]",
            "Rome": "[LOCATION-1]",
            "Kate": "[PERSON-2]",
            "Madrid": "[LOCATION-2]",
            "+380956784534": "[PHONE_NUMBER-1]",
            "katty@gmail.com": "[EMAIL_ADDRESS-1]",
        },

        env_vars={
            "PRESIDIO_CONFIDENCE_SCORE_THRESHOLD": "0.6",
            "PRESIDIO_CUSTOM_RECOGNIZERS_CONFIG": """
            - name: "EmployeeIdRecognizer"
              supported_entity: "EMPLOYEE_ID"
              patterns:
                - name: "EmployeeIdRegex"
                  regex: "GL-\\\\d{6}"
                  score: "0.5"
            """
        },
    ),

    TestCase(
        _INPUT_TEXT,

        "My name is [PERSON-1]. I live in [LOCATION-1] and work at Google. My employee id is [EMPLOYEE_ID-1]. In my spare time I play tennis. "
        + "[PERSON-2] is a friend of mine. She also works at Google, but she lives in [LOCATION-2] and loves football. "
        + "You can contact me by phone [PHONE_NUMBER-1] and [PERSON-2] by [EMAIL_ADDRESS-1].",

        {
            "John": "[PERSON-1]",
            "Rome": "[LOCATION-1]",
            "GL-456698": "[EMPLOYEE_ID-1]",
            "Kate": "[PERSON-2]",
            "Madrid": "[LOCATION-2]",
            "+380956784534": "[PHONE_NUMBER-1]",
            "katty@gmail.com": "[EMAIL_ADDRESS-1]",
        },

        env_vars={
            "PRESIDIO_CONFIDENCE_SCORE_THRESHOLD": "0.4",
            "PRESIDIO_CONTEXT_SIMILARITY_FACTOR": "0.15",
            "PRESIDIO_MIN_SCORE_WITH_CONTEXT_SIMILARITY": "0.45",
            "PRESIDIO_CUSTOM_RECOGNIZERS_CONFIG": """
            - name: "EmployeeIdRecognizer"
              supported_entity: "EMPLOYEE_ID"
              patterns:
                - name: "EmployeeIdRegex"
                  regex: "GL-\\\\d{6}"
                  score: "0.1"
              context:
                - "employee"
                - "id"
            """
        },
    ),

    TestCase(
        _INPUT_TEXT,

        "My name is [PERSON-1]. I live in [LOCATION-1] and work at Google. My employee id is [EMPLOYEE_ID-1]. In my spare time I play tennis. "
        + "[PERSON-2] is a friend of mine. She also works at Google, but she lives in [LOCATION-2] and loves football. "
        + "You can contact me by phone [PHONE_NUMBER-1] and [PERSON-2] by [EMAIL_ADDRESS-1].",

        {
            "John": "[PERSON-1]",
            "Rome": "[LOCATION-1]",
            "GL-456698": "[EMPLOYEE_ID-1]",
            "Kate": "[PERSON-2]",
            "Madrid": "[LOCATION-2]",
            "+380956784534": "[PHONE_NUMBER-1]",
            "katty@gmail.com": "[EMAIL_ADDRESS-1]",
        },

        env_vars={
            "PRESIDIO_CONFIDENCE_SCORE_THRESHOLD": "0.55",
            "PRESIDIO_CONTEXT_SIMILARITY_FACTOR": "0.15",
            "PRESIDIO_MIN_SCORE_WITH_CONTEXT_SIMILARITY": "0.45",
            "PRESIDIO_CUSTOM_RECOGNIZERS_CONFIG": """
            - name: "EmployeeIdRecognizer"
              supported_entity: "EMPLOYEE_ID"
              patterns:
                - name: "EmployeeIdRegex"
                  regex: "GL-\\\\d{6}"
                  score: "0.5"
              context:
                - "employee"
                - "id"
            """
        },
    ),
]


@pytest.fixture
def set_env_vars(monkeypatch, test_case):
    env_vars = test_case.env_vars or {}

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    import aidial_interceptors_sdk.examples.chat_completion.presidio_anonymizer.analyzer
    importlib.reload(aidial_interceptors_sdk.examples.chat_completion.presidio_anonymizer.analyzer)

    import aidial_interceptors_sdk.examples.chat_completion.presidio_anonymizer.recognizers_config
    importlib.reload(aidial_interceptors_sdk.examples.chat_completion.presidio_anonymizer.recognizers_config)


@pytest.fixture
def anonymizer():
    return PresidioAnonymizer()


@pytest.mark.parametrize("test_case", test_cases)
async def test_presidio_anonymize_deanonymize(
        test_case: TestCase, set_env_vars, anonymizer: Anonymizer
):
    text = test_case.original_text
    expected_replacements = test_case.replacements
    expected_anonymized = test_case.anonymized_text

    anon = await anonymizer.collect_replacements(text)
    anonymized = anon.anonymize(text)
    assert expected_anonymized == anonymized

    deanonymized = anon.deanonymize(anonymized)

    assert anon.replacements == expected_replacements

    for key in anon.replacements:
        assert key not in anonymized
        assert key in text
        assert key in deanonymized

    assert text == deanonymized
