from typing import List
import yaml
import logging

from aidial_interceptors_sdk.utils._env import get_env_or_default

from presidio_analyzer import PatternRecognizer
from presidio_analyzer import EntityRecognizer
from presidio_analyzer import RecognizerRegistry
from presidio_analyzer import Pattern

_PRESIDIO_CUSTOM_RECOGNIZERS_CONFIG = get_env_or_default("PRESIDIO_CUSTOM_RECOGNIZERS_CONFIG", None)

_log = logging.getLogger(__name__)


def add_custom_recognizers(recognizer_registry: RecognizerRegistry):
    if not _PRESIDIO_CUSTOM_RECOGNIZERS_CONFIG:
        return

    try:
        custom_recognizers = yaml.safe_load(_PRESIDIO_CUSTOM_RECOGNIZERS_CONFIG)
        if not custom_recognizers:
            return
        if not isinstance(custom_recognizers, list):
            raise TypeError("Custom recognizers configuration must be a list of dictionaries.")

        _log.debug(
            f"CUSTOM_RECOGNIZERS_CONFIG: '{custom_recognizers}' has been parsed."
        )

        for recognizer_config in custom_recognizers:
            name = recognizer_config.get("name")
            supported_entity = recognizer_config.get("supported_entity")
            context_words = recognizer_config.get("context", [])

            patterns: List[Pattern] = []
            patterns_config = recognizer_config.get("patterns", [])

            for patterns_config in patterns_config:
                pattern_name = patterns_config.get("name")
                pattern_regex = patterns_config.get("regex")
                pattern_score = patterns_config.get("score")
                patterns.append(create_pattern(pattern_name, pattern_regex, float(pattern_score)))

            recognizer = create_recognizer(
                name=name, supported_entity=supported_entity, patterns=patterns, context=context_words
            )
            recognizer_registry.add_recognizer(recognizer)

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format in PRESIDIO_CUSTOM_RECOGNIZERS_CONFIG: {e}")
    except Exception as e:
        raise RuntimeError(f"An error occurred while adding custom recognizers: {e}")


def create_pattern(name: str, regex: str, score: float) -> Pattern:
    return Pattern(name=name, regex=regex, score=score)


def create_recognizer(name: str, supported_entity: str, patterns: List[Pattern], context: List[str]) -> EntityRecognizer:
    return PatternRecognizer(
        name=name,
        supported_entity=supported_entity,
        patterns=patterns,
        context=context
    )
