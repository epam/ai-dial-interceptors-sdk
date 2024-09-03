import logging
from abc import ABC
from typing import List

from aidial_sdk.pydantic_v1 import BaseModel

from aidial_interceptors_sdk.dial_client import DialClient

_log = logging.getLogger(__name__)


class EmbeddingsInterceptor(ABC, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    dial_client: DialClient

    async def modify_input(self, input: str) -> str:
        return input

    async def modify_embedding(
        self, embedding: str | List[float]
    ) -> str | List[float]:
        return embedding

    async def modify_request(self, request: dict) -> dict:
        if "input" in request:
            input = request["input"]
            if isinstance(input, str):
                request["input"] = await self.modify_input(input)
            elif isinstance(input, list):
                if all(isinstance(item, str) for item in input):
                    request["input"] = [
                        await self.modify_input(item) for item in input
                    ]
            else:
                _log.warning("Tokenized input isn't yet supported")

        return request

    async def modify_response(self, response: dict) -> dict:
        for item in response.get("data") or []:
            item["embedding"] = await self.modify_embedding(item["embedding"])
        return response


class EmbeddingsNoOpInterceptor(EmbeddingsInterceptor):
    pass
