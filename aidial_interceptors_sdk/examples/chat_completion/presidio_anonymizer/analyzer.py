from typing import List
from typing import Optional
import logging

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.nlp_engine import SpacyNlpEngine
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer import RecognizerResult

from aidial_interceptors_sdk.utils._env import get_env_or_default

from .recognizers_config import add_custom_recognizers
from .nlp_model_config import get_models_per_lang

_PRESIDIO_CONTEXT_SIMILARITY_FACTOR = get_env_or_default("PRESIDIO_CONTEXT_SIMILARITY_FACTOR", "0.35")
_PRESIDIO_MIN_SCORE_WITH_CONTEXT_SIMILARITY = get_env_or_default("PRESIDIO_MIN_SCORE_WITH_CONTEXT_SIMILARITY", "0.3")
_PRESIDIO_ALLOW_LIST = get_env_or_default("PRESIDIO_ALLOW_LIST")
_PRESIDIO_CONFIDENCE_SCORE_THRESHOLD = get_env_or_default("PRESIDIO_CONFIDENCE_SCORE_THRESHOLD", "0.5")


_log = logging.getLogger(__name__)


def get_context_similarity_factor() -> float:
    try:
        similarity_factor = float(_PRESIDIO_CONTEXT_SIMILARITY_FACTOR)

        if not (0.0 <= similarity_factor <= 1.0):
            raise ValueError(
                f"PRESIDIO_CONTEXT_SIMILARITY_FACTOR must be between 0 and 1. Got: {similarity_factor}"
            )

        return similarity_factor
    except ValueError as e:
        raise ValueError(
            f"PRESIDIO_CONTEXT_SIMILARITY_FACTOR must be a valid float. Got: {_PRESIDIO_CONTEXT_SIMILARITY_FACTOR}. Error: {e}"
        )


def get_min_score_with_context_similarity() -> float:
    try:
        min_score_with_context_similarity = float(_PRESIDIO_MIN_SCORE_WITH_CONTEXT_SIMILARITY)

        if not (0.0 <= min_score_with_context_similarity <= 1.0):
            raise ValueError(
                f"PRESIDIO_MIN_SCORE_WITH_CONTEXT_SIMILARITY must be between 0 and 1. Got: {min_score_with_context_similarity}"
            )

        return min_score_with_context_similarity
    except ValueError as e:
        raise ValueError(
            f"PRESIDIO_MIN_SCORE_WITH_CONTEXT_SIMILARITY must be a valid float. Got: {_PRESIDIO_MIN_SCORE_WITH_CONTEXT_SIMILARITY}. Error: {e}"
        )


def get_confidence_score_threshold() -> float:
    try:
        confidence_score_threshold = float(_PRESIDIO_CONFIDENCE_SCORE_THRESHOLD)

        if not (0.0 <= confidence_score_threshold <= 1.0):
            raise ValueError(
                f"PRESIDIO_CONFIDENCE_SCORE_THRESHOLD must be between 0 and 1. Got: {confidence_score_threshold}"
            )

        return confidence_score_threshold
    except ValueError as e:
        raise ValueError(
            f"PRESIDIO_CONFIDENCE_SCORE_THRESHOLD must be a valid float. Got: {_PRESIDIO_CONFIDENCE_SCORE_THRESHOLD}. Error: {e}"
        )


def get_pii_analyzer() -> AnalyzerEngine:
    models = get_models_per_lang()
    nlp_engine = get_nlp_engine(models)
    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=list(models.keys()),
        context_aware_enhancer=LemmaContextAwareEnhancer(
            context_similarity_factor=get_context_similarity_factor(),
            min_score_with_context_similarity=get_min_score_with_context_similarity()
        ),
    )

    add_custom_recognizers(analyzer.registry)

    return analyzer


def get_nlp_engine(models_per_lang: dict[str, str]) -> SpacyNlpEngine:
    nlp_configuration = get_nlp_configuration(models_per_lang)
    provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
    return provider.create_engine()


def get_nlp_configuration(models_per_lang: dict[str, str]) -> dict:
    formatted_models = [
        {"lang_code": lang, "model_name": model}
        for lang, model in models_per_lang.items()
    ]
    _log.debug(
        f"formatted_models: {formatted_models}\n"
    )
    return {
        "nlp_engine_name": "spacy",
        "models": formatted_models
    }


def get_allow_list() -> Optional[List[str]]:
    allow_list = get_env_or_default("PRESIDIO_ALLOW_LIST")
    if allow_list is None:
        return None

    allow_list = [item.strip() for item in allow_list.split(",")]

    if not all(isinstance(item, str) and item for item in allow_list):
        raise ValueError("PRESIDIO_ALLOW_LIST must be a comma-separated list of non-empty strings.")

    return allow_list


class PresidioAnalyzer:
    _analyzer_engine: AnalyzerEngine
    _confidence_score_threshold: float
    _allow_list: Optional[List[str]]

    def __init__(self):
        self._analyzer_engine = get_pii_analyzer()
        self._confidence_score_threshold = get_confidence_score_threshold()
        self._allow_list = get_allow_list()

    def analyze(self, content: str, language: str) -> List[RecognizerResult]:
        return self._analyzer_engine.analyze(
            text=content, language=language, score_threshold=self._confidence_score_threshold, allow_list=self._allow_list
        )

    def get_supported_entities(self) -> List[str]:
        return self._analyzer_engine.get_supported_entities()

    def get_supported_languages(self) -> List[str]:
        return self._analyzer_engine.supported_languages
