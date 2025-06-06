from ..anonymizer.base import Anonymizer
from ..anonymizer.impl import AnonymizerInterceptor
from .anonymizer import SpacyAnonymizer


class SpacyAnonymizerInterceptor(AnonymizerInterceptor):
    def get_anonymizer(self) -> Anonymizer:
        return SpacyAnonymizer()
