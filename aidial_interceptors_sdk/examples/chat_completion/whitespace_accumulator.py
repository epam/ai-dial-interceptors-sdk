import logging
import time

from aidial_sdk.chat_completion.chunks import ContentChunk
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)

_log = logging.getLogger(__name__)

_FLUSH_TIMEOUT = 1.0


class WhitespaceAccumulatorInterceptor(ChatCompletionInterceptor):
    buffer: list[str] = []
    start: float = 0.0
    timeout: float = _FLUSH_TIMEOUT
    send_content = False

    def flush(self) -> str:
        _log.debug(f"flushed {len(self.buffer)} elements")
        content = "".join(self.buffer)
        self.buffer.clear()
        self.start = time.perf_counter()
        return content

    def need_flush(self, data: str) -> bool:
        passed = time.perf_counter() - self.start
        return not data.isspace() or (passed > self.timeout)

    def get_content(self, chunk: dict) -> str:
        try:
            return (
                chunk["choices"][0]["delta"].get("content")
                or chunk["choices"][0]["message"].get("content")
                or ""
            )
        except (KeyError, IndexError, TypeError):
            return ""

    def set_content(self, chunk: dict, content: str) -> None:
        if content == "":
            return

        try:
            if "delta" in chunk["choices"][0]:
                chunk["choices"][0]["delta"]["content"] = content
            elif "message" in chunk["choices"][0]:
                chunk["choices"][0]["message"]["content"] = content
            else:
                return
        except (KeyError, IndexError, TypeError):
            return

    @override
    async def on_stream_start(self) -> None:
        self.start = time.perf_counter()

    @override
    async def on_stream_chunk(self, chunk: dict) -> None:
        content = self.get_content(chunk)
        if content == "":
            self.send_chunk(chunk)
            return

        if self.need_flush(content):
            flushed = self.flush()
            self.set_content(chunk, flushed + content)
            self.send_chunk(chunk)
            self.send_content = True
        else:
            _log.debug("buffered content")
            self.buffer.append(content)

    @override
    async def on_stream_end(self) -> None:
        if len(self.buffer) == 0:
            return
        flushed = self.flush()
        chunk = ContentChunk(flushed, 0)
        if self.send_content is True:
            self.send_chunk(chunk)
        else:
            with self.response.create_single_choice() as choice:
                choice.send_chunk(chunk)
