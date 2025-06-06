from ..anonymizer.base import Anonymizer
from ..anonymizer.impl import AnonymizerInterceptor
from .anonymizer import SpacyAnonymizer


class SpacyAnonymizerInterceptor(AnonymizerInterceptor):
    def get_anonymizer(self, config: dict) -> Anonymizer:
        return SpacyAnonymizer()

    def get_anonymizer_config_field_name(self) -> str | None:
        return None
