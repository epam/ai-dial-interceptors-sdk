import logging
import time

from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)

_log = logging.getLogger(__name__)

_FLUSH_TIMEOUT = 1.0


class WhitespaceAccumulatorInterceptor(ChatCompletionInterceptor):
    last_send: float = 0.0
    cur_chunk: dict | None = None
    cur_chunks: int = 0
    timeout_sec: float = _FLUSH_TIMEOUT
    buffer: list[str] = []

    def save_to_cache(self, chunk: dict):
        self.cur_chunk = chunk
        if content := self.get_content(chunk):
            self.buffer.append(content)

    def flush(self) -> None:
        assert self.cur_chunk is not None
        _log.info(f"flushed {self.cur_chunks} chunks")
        self.last_send = time.perf_counter()
        content = "".join(self.buffer)
        self.set_content(self.cur_chunk, content)
        self.send_chunk(self.cur_chunk)
        self.buffer.clear()
        self.cur_chunk = None
        self.cur_chunks = 0

    def flush_if_needed(self) -> None:
        if self.cur_chunk:
            self.flush()

    def need_flush(self, content: str | None) -> bool:
        passed = time.perf_counter() - self.last_send
        return content and not content.isspace() or (passed > self.timeout_sec)

    def get_content(self, chunk: dict) -> str | None:
        try:
            return chunk["choices"][0]["delta"].get("content")
        except (KeyError, IndexError, TypeError):
            return None

    def set_content(self, chunk: dict, content: str):
        try:
            chunk["choices"][0]["delta"]["content"] = content
        except (KeyError, IndexError, TypeError):
            return None

    def set_chunk_if_needed(self, chunk: dict):
        if not self.cur_chunk:
            self.cur_chunk = chunk

    def match_cache_structure(self, chunk: dict) -> bool:
        if not ("choices" in chunk.keys()):
            return False

        choices = chunk.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            return False

        choice = choices[0]
        if not isinstance(choice, dict) or set(choice.keys()) != {
            "delta",
            "index",
            "finish_reason",
        }:
            return False

        delta = choice["delta"]
        if not isinstance(delta, dict) or not set(delta.keys()).issubset(
            {
                "content",
                "role",
            }
        ):
            return False

        finish_reason = choice["finish_reason"]
        if finish_reason:
            return False

        return True

    @override
    async def on_stream_start(self) -> None:
        self.last_send = time.perf_counter()

    @override
    async def on_stream_chunk(self, chunk: dict) -> None:
        if self.match_cache_structure(chunk):
            self.set_chunk_if_needed(chunk)
            content = self.get_content(chunk)
            if content:
                self.buffer.append(content)
            if self.need_flush(content):
                self.flush()
            else:
                self.cur_chunks += 1
        else:
            self.flush_if_needed()
            self.send_chunk(chunk)

    @override
    async def on_stream_end(self) -> None:
        self.flush_if_needed()
