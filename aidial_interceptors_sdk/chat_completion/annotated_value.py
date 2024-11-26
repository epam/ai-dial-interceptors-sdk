from abc import ABC
from typing import Any

from aidial_sdk.exceptions import HTTPException as DialException
from aidial_sdk.pydantic_v1 import BaseModel


class AnnotatedValueBase(BaseModel, ABC):
    class Config:
        arbitrary_types_allowed = True

    annotation: Any | None = None


class AnnotatedChunk(AnnotatedValueBase):
    chunk: dict


class AnnotatedException(AnnotatedValueBase):
    error: DialException


AnnotatedValue = AnnotatedChunk | AnnotatedException
