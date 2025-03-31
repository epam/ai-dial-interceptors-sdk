from typing import (
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    List,
    Tuple,
    TypeVar,
)

import aiostream
from aidial_sdk.chat_completion import Stage
from aidial_sdk.chat_completion.chunks import (
    ContentChunk,
    EndChoiceChunk,
    FinishReason,
    UsageChunk,
)
from aidial_sdk.exceptions import HTTPException as DialException
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.annotated_value import (
    AnnotatedValue,
    Annotation,
)
from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
    RequestDict,
)
from aidial_interceptors_sdk.chat_completion.element_path import ElementPath
from aidial_interceptors_sdk.chat_completion.index_mapper import IndexMapper
from aidial_interceptors_sdk.utils.not_given import NotGiven
from aidial_interceptors_sdk.utils.streaming import annotate_stream


class ReplicatorInterceptor(ChatCompletionInterceptor):
    """
    Call the upstream model N time and combine the results into a single response.
    """

    # Interceptor parameter
    n: int

    # Response data
    content_stages: Dict[int, Stage] = {}
    stage_index_mapper: IndexMapper[Tuple[int, int]] = IndexMapper()

    total_usage: UsageChunk = UsageChunk(0, 0)
    finish_reasons: Dict[int, str] = {}
    role_sent: bool = False
    chunk_template: dict = {}

    def _accumulate_usage(self, usage: Dict) -> None:
        self.total_usage.prompt_tokens += usage.get("prompt_tokens") or 0
        self.total_usage.completion_tokens += (
            usage.get("completion_tokens") or 0
        )

    def _get_content_stage(self, path: ElementPath) -> Stage:
        response_idx = path.response_ctx
        assert isinstance(response_idx, int)

        if response_idx not in self.content_stages:
            stage = Stage(
                self.response._queue,
                0,
                self.stage_index_mapper((response_idx, -1)),
                f"{response_idx+1} | CONTENT",
            )
            stage.open()
            self.content_stages[response_idx] = stage

        return self.content_stages[response_idx]

    @override
    async def call_upstreams(
        self,
        request: RequestDict,
        call_upstream: Callable[
            [Annotation, RequestDict],
            Awaitable[AsyncIterator[dict | DialException]],
        ],
    ) -> AsyncIterator[AnnotatedValue]:
        request["n"] = 1

        streams = [
            annotate_stream(idx, await call_upstream(idx, request))
            for idx in range(self.n)
        ]
        # TODO: create tasks
        return _join_iterators(streams)

    @override
    async def on_response_stage(
        self, path: ElementPath, stage: dict
    ) -> List[dict] | dict:
        assert path.stage_idx is not None
        assert isinstance(path.response_ctx, int)

        if name := stage.get("name"):
            stage["name"] = f"{path.response_ctx+1} | {name}"

        stage["index"] = self.stage_index_mapper(
            (path.response_ctx, path.stage_idx)
        )

        return [stage]

    @override
    async def on_response_message(
        self, path: ElementPath, message: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        if message:
            # Avoid sending role multiple times
            if message.get("role"):
                if self.role_sent:
                    del message["role"]
                else:
                    self.role_sent = True

            # Rerouting message content to a dedicated content stage
            if content := message.get("content"):
                self._get_content_stage(path).append_content(content)
                message["content"] = ""

            if cc := message.get("custom_content"):
                if attachments := cc.get("attachments"):
                    for attachment in attachments:
                        self._get_content_stage(path).add_attachment(
                            **attachment
                        )
                    del cc["attachments"]

        return message

    @override
    async def on_response_finish_reason(
        self, path: ElementPath, finish_reason: str | NotGiven | None
    ) -> str | NotGiven | None:
        assert isinstance(path.response_ctx, int)

        if finish_reason:
            self.finish_reasons[path.response_ctx + 1] = finish_reason

        return None

    @override
    async def on_response_usage(
        self, usage: Dict | NotGiven | None
    ) -> Dict | NotGiven | None:

        # TODO: combine statistics.usage_per_model
        if usage:
            self._accumulate_usage(usage)

        return None

    @override
    async def on_stream_chunk(self, chunk: dict) -> None:
        if not self.chunk_template:
            self.chunk_template = {
                k: v
                for k, v in chunk.items()
                if k in ["id", "created", "system_fingerprint"]
            }

        self.send_chunk(self.chunk_template | chunk)

    # TODO: support streaming errors

    @override
    async def on_stream_end(self) -> None:
        content = "\n\n".join(
            [
                "Total usage:",
                f" * Prompt tokens: {self.total_usage.prompt_tokens}",
                f" * Completion tokens: {self.total_usage.completion_tokens}",
                "Finish reasons:",
                f" * {str(self.finish_reasons)}",
            ]
        )
        self.send_chunk(ContentChunk(content, 0))

        self.send_chunk(self.total_usage)

        for stage in self.content_stages.values():
            stage.close()

        finish_reason = (
            FinishReason.STOP
            if not self.finish_reasons
            else FinishReason(self.finish_reasons[1])
        )
        self.send_chunk(EndChoiceChunk(finish_reason, 0))


_T = TypeVar("_T")


async def _join_iterators(iters: List[AsyncIterator[_T]]) -> AsyncIterator[_T]:
    async with aiostream.stream.merge(*iters).stream() as combine:
        async for item in combine:
            yield item
