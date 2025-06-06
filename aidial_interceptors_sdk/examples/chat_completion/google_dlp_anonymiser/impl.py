from aidial_interceptors_sdk.utils._env import get_env

from ..anonymizer.base import Anonymizer
from ..anonymizer.impl import AnonymizerInterceptor
from .anonymizer import GoogleDLPAnonymizer
from .config import DeIdentificationConfig


class GoogleDLPAnonymizerInterceptor(AnonymizerInterceptor):
    def get_anonymizer(self) -> Anonymizer:
        return GoogleDLPAnonymizer(
            get_env("GCP_PROJECT_ID"), DeIdentificationConfig()
        )
