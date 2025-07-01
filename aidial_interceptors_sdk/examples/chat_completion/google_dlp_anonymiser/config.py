from typing import List

from pydantic import BaseModel

from aidial_interceptors_sdk.utils._env import get_env_list

_DEFAULT_INFO_TYPES = get_env_list(
    "GOOGLE_DLP_ANONYMIZER_INFO_TYPES_TO_DE_IDENTIFY",
    ["PHONE_NUMBER", "FIRST_NAME", "LAST_NAME"],
)


class DeIdentificationConfig(BaseModel):
    class Config:
        extra = "allow"

    info_types: List[str] = _DEFAULT_INFO_TYPES


class GoogleDLPAnonymizerConfig(BaseModel):
    class Config:
        extra = "allow"

    deidentification_config: DeIdentificationConfig = DeIdentificationConfig()
