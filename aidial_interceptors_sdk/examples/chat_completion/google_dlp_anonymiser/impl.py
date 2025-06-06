import json
import logging

from aidial_interceptors_sdk.utils._env import get_env

from ..anonymizer.base import Anonymizer
from ..anonymizer.impl import AnonymizerInterceptor
from .anonymizer import GoogleDLPAnonymizer
from .config import GoogleDLPAnonymizerConfig

_log = logging.getLogger(__name__)


class GoogleDLPAnonymizerInterceptor(AnonymizerInterceptor):
    def get_anonymizer(self, config: dict) -> Anonymizer:
        _log.debug(f"Google DLP configuration: {json.dumps(config)}")
        try:
            conf = GoogleDLPAnonymizerConfig.parse_obj(config)
        except Exception as e:
            _log.error(f"Unable to parse the request configuration: {e}")
            conf = GoogleDLPAnonymizerConfig()

        return GoogleDLPAnonymizer(
            get_env("GCP_PROJECT_ID"), conf.deidentification_config
        )

    def get_anonymizer_config_field_name(self) -> str | None:
        return "google_dlp_anonymizer"
