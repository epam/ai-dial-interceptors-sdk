import json
import logging
from functools import cache
from typing import Dict

from spacy import load as load_spacy_model
from spacy.cli.download import download as download_spacy_model
from spacy.language import Language
from spacy_langdetect import LanguageDetector

from aidial_interceptors_sdk.utils._env import get_env_or_default

from .nlp_model_training import (
    create_custom_trained_model,
    get_custom_trained_model_name,
)

_PRESIDIO_USE_CUSTOM_TRAINED_NLP_MODEL: str = get_env_or_default(
    "PRESIDIO_USE_CUSTOM_TRAINED_NLP_MODEL", "false"
)

_PRESIDIO_NLP_MODELS_PER_LANG: str = get_env_or_default(
    "PRESIDIO_NLP_MODELS_PER_LANG", '{"en": "en_core_web_sm"}'
)

_PRESIDIO_NLP_MODEL_FOR_LANG_DETECTION: str = get_env_or_default(
    "PRESIDIO_NLP_MODEL_FOR_LANG_DETECTION", "en_core_web_sm"
)


_log = logging.getLogger(__name__)


def get_models_per_lang() -> Dict[str, str]:
    models_per_lang = load_models_per_lang()

    if _PRESIDIO_USE_CUSTOM_TRAINED_NLP_MODEL.lower() not in {"true", "false"}:
        raise ValueError(
            "Invalid value for PRESIDIO_USE_CUSTOM_TRAINED_NLP_MODEL. Must be 'true' or 'false'."
        )

    if _PRESIDIO_USE_CUSTOM_TRAINED_NLP_MODEL.lower() == "true":
        return {
            key: get_custom_trained_model_name(key)
            for key in models_per_lang.keys()
        }

    return models_per_lang


def load_models_per_lang() -> Dict[str, str]:
    try:
        models_per_lang = json.loads(_PRESIDIO_NLP_MODELS_PER_LANG)

        if not isinstance(models_per_lang, dict) or not all(
            isinstance(k, str) and isinstance(v, str)
            for k, v in models_per_lang.items()
        ):
            raise TypeError("The parsed data must be a dictionary of strings.")

        return models_per_lang
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON format for NLP models per language: {e}"
        ) from e
    except TypeError as e:
        raise ValueError(
            f"Invalid structure for NLP models per language: {e}"
        ) from e


@Language.factory("language_detector")
def create_language_detector(nlp, name):
    return LanguageDetector()


@cache
def load_model(model_name: str) -> Language:
    try:
        nlp = load_spacy_model(model_name)
        nlp.add_pipe("language_detector", last=True)
        return nlp
    except OSError as e:
        _log.warning(
            f"Failed to load spaCy model {model_name!r}: {str(e)}\nDownloading the model..."
        )
        download_spacy_model(model_name)
        _log.info(f"Model '{model_name}' has been successfully installed.")
        return load_model(model_name)


def init_nlp_models():
    models_per_lang = load_models_per_lang()
    for lang, model_name in models_per_lang.items():
        base_model = load_model(model_name)
        if _PRESIDIO_USE_CUSTOM_TRAINED_NLP_MODEL.lower() == "true":
            create_custom_trained_model(base_model, lang)

    load_model(_PRESIDIO_NLP_MODEL_FOR_LANG_DETECTION)


init_nlp_models()
