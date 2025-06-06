from typing import List

from pydantic import BaseModel


class DeIdentificationConfig(BaseModel):
    info_types: List[str] = ["PHONE_NUMBER", "FIRST_NAME", "LAST_NAME"]
