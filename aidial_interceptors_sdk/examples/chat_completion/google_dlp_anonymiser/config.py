from typing import List

from pydantic import BaseModel


class DeIdentificationConfig(BaseModel):
    class Config:
        extra = "allow"

    info_types: List[str] = ["PHONE_NUMBER", "FIRST_NAME", "LAST_NAME"]


class GoogleDLPAnonymizerConfig(BaseModel):
    class Config:
        extra = "allow"

    deidentification_config: DeIdentificationConfig = DeIdentificationConfig()
