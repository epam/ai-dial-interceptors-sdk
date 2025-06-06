import logging

from google.cloud.dlp_v2 import DlpServiceClient, Likelihood

from aidial_interceptors_sdk.examples.utils.json import json_dumps_short
from aidial_interceptors_sdk.utils._env import get_env

from .config import DeIdentificationConfig

_log = logging.getLogger(__name__)


class DlpClient:
    _client: DlpServiceClient
    _parent: str
    _config: DeIdentificationConfig

    def __init__(self, project: str, config: DeIdentificationConfig):
        self._parent = f"projects/{project}/locations/global"
        self._client = DlpServiceClient()
        self._config = config

    def anonymize(self, input: str) -> str:
        info_types = [{"name": ty} for ty in self._config.info_types]

        transformation = {
            "info_types": info_types,
            "primitive_transformation": {"replace_with_info_type_config": {}},
        }

        deidentify_config = {
            "info_type_transformations": {"transformations": [transformation]},
            # Keeping potentially sensitive information if it was not possible to parse it.
            "transformation_error_handling": {"leave_untransformed": {}},
        }

        inspect_config = {
            "info_types": info_types,
            "min_likelihood": Likelihood.UNLIKELY,
        }

        item = {"value": input}

        request = {
            "parent": self._parent,
            "deidentify_config": deidentify_config,
            "inspect_config": inspect_config,
            "item": item,
        }

        if _log.isEnabledFor(logging.DEBUG):
            _log.debug(f"deidentify request: {json_dumps_short(request)}")

        response = self._client.deidentify_content(request=request)

        if _log.isEnabledFor(logging.DEBUG):
            _log.debug(f"deidentify response: {json_dumps_short(response)}")

        return response.item.value


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)
    client = DlpClient(get_env("GCP_PROJECT_ID"), DeIdentificationConfig())
    s = "My phone number is 08825 20 35. And my name is John Smith."
    s2 = client.anonymize(s)
    print(s2)
