import logging
from functools import cache

from aidial_sdk.pydantic_v1 import BaseModel
from spacy import load as load_model
from spacy.cli.download import download as download_model
from spacy.language import Language

from aidial_interceptors_sdk.utils._env import get_env_list, get_envs

from ..anonymizer.base import Anonymizer
from ..anonymizer.replacement import Replacement
from ..anonymizer.replacements import Replacements

_log = logging.getLogger(__name__)

# Find spaCy models here: https://spacy.io/models/
# NOTE: Pinning the version of en_core_web_sm:
# https://github.com/explosion/spaCy/issues/13690#issuecomment-2487873386
# otherwise, there is a chance of running into 403 error in runtime.
_DEFAULT_MODEL = "en_core_web_sm-3.7.1"

# Find the full list of entities here:
# https://github.com/explosion/spacy-models/blob/e46017f5c8241096c1b30fae080f0e0709c8038c/meta/en_core_web_sm-3.7.0.json#L121-L140
_DEFAULT_LABELS_TO_REDACT = [
    "PERSON",
    "ORG",
    "GPE",  # Geo-political entity
    "PRODUCT",
]


@cache
def _get_pipeline(model: str) -> Language:
    model_name = model.partition("-")[0]  # dropping a version
    try:
        return load_model(model_name)
    except Exception as e:
        _log.warning(
            f"Failed to load spaCy model {model!r}: {str(e)}\nDownloading the model..."
        )
        download_model(model, direct=True)
        return load_model(model_name)


# Preemptively load the default model on the server start-up
# to avoid waiting during the first request.
_get_pipeline(_DEFAULT_MODEL)

_LABELS_TO_REDACT = get_envs(
    [
        "PII_ANONYMIZER_LABELS_TO_REDACT",
        "SPACY_ANONYMIZER_LABELS_TO_REDACT",
    ],
    get_env_list,
    _DEFAULT_LABELS_TO_REDACT,
)


class SpacyAnonymizer(BaseModel, Anonymizer):
    def _is_replacement(self, text: str, start: int, end: int) -> bool:
        return bool(
            Replacement.parse(text[start:end])
            or Replacement.parse(
                text[max(0, start - 1) : min(end + 1, len(text))]
            )
        )

    async def collect_replacements(
        self, text: str, *, replacements: Replacements | None = None
    ) -> Replacements:
        doc = _get_pipeline(_DEFAULT_MODEL)(text)

        replacements = replacements or Replacements()
        for ent in doc.ents:
            if ent.label_ in _LABELS_TO_REDACT and not self._is_replacement(
                doc.text, ent.start_char, ent.end_char
            ):
                replacements.get_replacement(ent.label_, ent.text)

        return replacements
