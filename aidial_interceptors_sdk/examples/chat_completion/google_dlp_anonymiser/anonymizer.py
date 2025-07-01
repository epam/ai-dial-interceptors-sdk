from aidial_sdk.exceptions import InternalServerError

from ..anonymizer.base import Anonymizer
from ..anonymizer.replacement import Replacements, create_indexed_replacements
from .client import DlpClient
from .config import DeIdentificationConfig


class GoogleDLPAnonymizer(Anonymizer):
    _client: DlpClient
    _config: DeIdentificationConfig

    def __init__(self, project: str, config: DeIdentificationConfig):
        self._client = DlpClient(project, config)
        self._config = config

    async def collect_replacements(
        self, text: str, *, replacements: Replacements | None = None
    ) -> Replacements:
        anonymized = await self._client.anonymize(text)

        replacements = replacements or Replacements()
        replacements = create_indexed_replacements(
            replacements, self._config.info_types, text, anonymized
        )
        if replacements is None:
            raise InternalServerError(
                "It wasn't possible to parse the anonymized text"
            )
        return replacements
