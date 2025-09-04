from aidial_interceptors_sdk.utils._env import get_env

from ..anonymizer.base import Anonymizer
from ..anonymizer.impl import AnonymizerInterceptor
from .anonymizer import GoogleDLPAnonymizer
from .config import GoogleDLPAnonymizerConfig


class GoogleDLPAnonymizerInterceptor(AnonymizerInterceptor):
    @classmethod
    async def configuration_schema(cls):
        return GoogleDLPAnonymizerConfig

    def get_anonymizer(self) -> Anonymizer:
        conf = self.get_configuration(GoogleDLPAnonymizerConfig)

        return GoogleDLPAnonymizer(
            get_env("GCP_PROJECT_ID"), conf.deidentification_config
        )
