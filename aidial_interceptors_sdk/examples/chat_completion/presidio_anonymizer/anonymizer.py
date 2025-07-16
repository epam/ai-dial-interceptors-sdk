import logging
from typing import List

from aidial_sdk.exceptions import InternalServerError
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.entities.engine.recognizer_result import (
    RecognizerResult as AnonymizerRecognizerResult,
)

from aidial_interceptors_sdk.utils._env import get_env_or_default

from ..anonymizer.base import Anonymizer
from ..anonymizer.replacement import Replacements, create_indexed_replacements
from .analyzer import PresidioAnalyzer
from .nlp_model_config import _PRESIDIO_NLP_MODEL_FOR_LANG_DETECTION, load_model

_PRESIDIO_IGNORE_PII_DETECTION_FOR_UNKNOWN_LANG = get_env_or_default(
    "PRESIDIO_IGNORE_PII_DETECTION_FOR_UNKNOWN_LANG", "false"
)

_log = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    nlp = load_model(_PRESIDIO_NLP_MODEL_FOR_LANG_DETECTION)
    detected_language = nlp(text)._.language["language"]
    _log.debug(f"detected_language is: {detected_language}\n")
    return detected_language


def ignore_pii_detection(
    detected_language: str, supported_languages: List[str]
) -> bool:
    if detected_language not in supported_languages:
        if _PRESIDIO_IGNORE_PII_DETECTION_FOR_UNKNOWN_LANG.lower() not in {
            "true",
            "false",
        }:
            raise ValueError(
                "Invalid value for PRESIDIO_USE_CUSTOM_TRAINED_NLP_MODEL. Must be 'true' or 'false'."
            )

        if _PRESIDIO_IGNORE_PII_DETECTION_FOR_UNKNOWN_LANG.lower() == "true":
            return True

        raise InternalServerError(
            f"Detected Language: {detected_language} is not supported. Supported languages are: {supported_languages}\n"
        )
    return False


class PresidioAnonymizer(Anonymizer):
    _analyzer: PresidioAnalyzer
    _anonymizer_engine: AnonymizerEngine

    def __init__(self):
        self._analyzer = PresidioAnalyzer()
        self._anonymizer_engine = AnonymizerEngine()

    async def collect_replacements(
        self, text: str, *, replacements: Replacements | None = None
    ) -> Replacements:
        detected_language = detect_language(text)
        should_ignore_pii_detection = ignore_pii_detection(
            detected_language, self._analyzer.get_supported_languages()
        )

        if should_ignore_pii_detection:
            return replacements or Replacements()

        analyzer_results = self._analyzer.analyze(
            content=text, language=detected_language
        )
        _log.debug(f"analyzer_results: {analyzer_results}\n")

        analyzer_results_for_anonymizer = [
            AnonymizerRecognizerResult(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=result.score,
            )
            for result in analyzer_results
        ]

        pii_entity_types = self._analyzer.get_supported_entities()
        operators = {
            entity_type: OperatorConfig(
                "replace", {"new_value": f"[{entity_type}]"}
            )
            for entity_type in pii_entity_types
        }

        anonymized = self._anonymizer_engine.anonymize(
            text=text,
            analyzer_results=analyzer_results_for_anonymizer,
            operators=operators,
        )
        _log.debug(f"Anonymized text: {str(anonymized.text)}\n")
        replacements = replacements or Replacements()
        replacements = create_indexed_replacements(
            replacements, pii_entity_types, text, anonymized.text
        )
        if replacements is None:
            raise InternalServerError(
                "It wasn't possible to parse the anonymized text"
            )
        return replacements
