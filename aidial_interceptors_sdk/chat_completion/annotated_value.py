from abc import ABC
from typing import Any

from aidial_sdk.exceptions import HTTPException as DialException
from aidial_sdk.pydantic_v1 import BaseModel

Annotation = Any | None


class AnnotatedValueBase(BaseModel, ABC):
    class Config:
        arbitrary_types_allowed = True

    annotation: Annotation = None


class AnnotatedChunk(AnnotatedValueBase):
    chunk: dict


class AnnotatedException(AnnotatedValueBase):
    error: DialException


AnnotatedValue = AnnotatedChunk | AnnotatedException
