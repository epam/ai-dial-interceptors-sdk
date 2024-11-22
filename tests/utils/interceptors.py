from aidial_sdk.chat_completion.chunks import ContentChunk
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)


class TracingInterceptor(ChatCompletionInterceptor):
    # Interceptor parameter
    name: str

    traced_entered = False

    def _send_line(self, content: str):
        self.send_chunk(ContentChunk(content, 0))

    def _trace_enter(self):
        if not self.traced_entered:
            self.traced_entered = True
            self._send_line(f"{self.name}.enter\n")

    def _trace_exit(self):
        self._send_line(f"\n{self.name}.exit")

    @override
    async def on_stream_chunk(self, chunk: dict) -> None:
        self._trace_enter()
        self.send_chunk(chunk)

    @override
    async def on_stream_end(self) -> None:
        self._trace_exit()
