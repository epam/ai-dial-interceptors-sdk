from ..anonymizer.base import Anonymizer
from ..anonymizer.impl import AnonymizerInterceptor
from .anonymizer import PresidioAnonymizer


class PresidioAnonymizerInterceptor(AnonymizerInterceptor):

    def get_anonymizer(self, config: dict) -> Anonymizer:
        return PresidioAnonymizer()

    def get_anonymizer_config_field_name(self) -> str | None:
        return None
