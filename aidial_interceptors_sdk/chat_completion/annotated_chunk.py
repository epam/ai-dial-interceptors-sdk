from typing import Any

from openai import BaseModel


class AnnotatedChunk(BaseModel):
    chunk: dict
    annotation: Any | None = None
