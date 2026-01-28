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

    def flush(self) -> None:
        if self.cur_chunk is None:
            return
        if self.cur_chunks > 1:
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

    def need_flush(self, content: str) -> bool:
        passed = time.perf_counter() - self.last_send
        return content and not content.isspace() or (passed > self.timeout_sec)

    @staticmethod
    def set_content(chunk: dict, content: str):
        try:
            chunk["choices"][0]["delta"]["content"] = content
        except (KeyError, IndexError, TypeError):
            return None

    @staticmethod
    def parse_content_only_chunk(chunk: dict) -> str | None:
        if (choices := chunk.get("choices")) is None:
            return None

        if not isinstance(choices, list) or len(choices) != 1:
            return None

        choice = choices[0]
        if not isinstance(choice, dict) or set(choice.keys()) != {
            "finish_reason",
            "index",
            "delta",
        }:
            return None

        if choice["finish_reason"]:
            return None

        index = choice["index"]
        if not isinstance(index, int) or index != 0:
            return None

        delta = choice["delta"]
        if not isinstance(delta, dict) or set(delta.keys()) != {
            "content",
        }:
            return None

        content = delta["content"]
        if not isinstance(content, str):
            return None

        return content

    @override
    async def on_stream_start(self) -> None:
        self.last_send = time.perf_counter()

    @override
    async def on_stream_chunk(self, chunk: dict) -> None:
        if content := self.parse_content_only_chunk(chunk):
            self.cur_chunk = self.cur_chunk or chunk
            self.buffer.append(content)
            if self.need_flush(content):
                self.flush()
            else:
                self.cur_chunks += 1
        else:
            self.flush()
            self.send_chunk(chunk)

    @override
    async def on_stream_end(self) -> None:
        self.flush()
