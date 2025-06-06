import logging

from google.cloud.dlp_v2 import DlpServiceAsyncClient, Likelihood

from aidial_interceptors_sdk.examples.utils.json import json_dumps_short

from .config import DeIdentificationConfig

_log = logging.getLogger(__name__)


class DlpClient:
    _parent: str
    _client: DlpServiceAsyncClient
    _config: DeIdentificationConfig

    def __init__(self, project: str, config: DeIdentificationConfig):
        self._parent = f"projects/{project}/locations/global"
        self._client = DlpServiceAsyncClient()
        self._config = config

    async def anonymize(self, input: str) -> str:
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

        response = await self._client.deidentify_content(request=request)

        if _log.isEnabledFor(logging.DEBUG):
            _log.debug(f"deidentify response: {json_dumps_short(response)}")

        return response.item.value
