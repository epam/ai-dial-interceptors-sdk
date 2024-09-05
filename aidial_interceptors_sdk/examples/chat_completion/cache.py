import json
import logging
import time
import uuid

from aidial_sdk.utils.merge_chunks import merge
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from aidial_interceptors_sdk.error import EarlyStreamExit
from aidial_interceptors_sdk.examples.utils.lru_cache import LRUCache

_log = logging.getLogger(__name__)

_MAX_CACHE_SIZE = 1000
_LRU_CACHE = LRUCache[str, dict](maxsize=_MAX_CACHE_SIZE)


def _request_to_key(request: dict) -> str:
    return json.dumps(request, sort_keys=True, separators=(",", ":"))


def _merge_chunks(chunk1: dict, chunk2: dict) -> dict:
    # Avoid merging top-level keys
    for key in ["id", "created", "model", "object", "system_fingerprint"]:
        chunk1[key] = chunk1.get(key) or chunk2.get(key)
        if key in chunk2:
            del chunk2[key]

    return merge(chunk1, chunk2)


class CachingInterceptor(ChatCompletionInterceptor):
    request_key: str = ""
    response_merged: dict = {}

    @override
    async def on_request(self, request: dict) -> dict:
        self.request_key = _request_to_key(request)
        return request

    @override
    async def on_stream_start(self) -> None:
        cached_response = _LRU_CACHE.lookup(self.request_key)
        if cached_response is not None:
            cached_response["id"] = "chatcmpl-" + str(uuid.uuid4())
            cached_response["created"] = int(time.time())
            self.send_chunk(cached_response)
            _log.debug("Cache hit")
            raise EarlyStreamExit("Cache hit")

        _log.debug("Cache miss")

    @override
    async def on_stream_chunk(self, chunk: dict) -> None:
        self.response_merged = _merge_chunks(self.response_merged, chunk)
        self.send_chunk(chunk)

    @override
    async def on_stream_end(self) -> None:
        del self.response_merged["id"]
        del self.response_merged["created"]

        _LRU_CACHE.save(self.request_key, self.response_merged)
        _log.debug("Saved to cache")
