import time
from collections import defaultdict
from typing import Dict, List

from aidial_sdk.chat_completion import Stage
from aidial_sdk.pydantic_v1 import BaseModel
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from aidial_interceptors_sdk.chat_completion.element_path import ElementPath
from aidial_interceptors_sdk.examples.utils.dict import collect_at_path
from aidial_interceptors_sdk.examples.utils.markdown import MarkdownTable
from aidial_interceptors_sdk.utils.not_given import NotGiven


class UsagePerModel(BaseModel):
    index: int
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class StatisticsReporterInterceptor(ChatCompletionInterceptor):
    """
    Reports token usage, finish reason and generation speed in the first stage.
    """

    # Request data
    request_n: int = -1

    # Response data
    request_end_time: float = -1

    response_start_time: float = -1
    response_end_time: float = -1

    prompt_tokens: int = 0
    completion_tokens: int = 0

    usage_per_model: List[UsagePerModel] = []

    # Per-choice response data
    finish_reasons: Dict[int, str] = {}
    statistics_stages: Dict[int, Stage] = {}
    content_lengths: Dict[int, int] = defaultdict(int)

    @override
    async def on_response_usage(
        self, usage: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        if usage:
            self.prompt_tokens += usage["prompt_tokens"]
            self.completion_tokens += usage["completion_tokens"]
        return usage

    @override
    async def on_response_finish_reason(
        self, path: ElementPath, finish_reason: str | NotGiven | None
    ) -> str | NotGiven | None:
        if finish_reason and path.choice_idx is not None:
            self.finish_reasons[path.choice_idx] = finish_reason
        return finish_reason

    @override
    async def on_response_message(
        self, path: ElementPath, message: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        if (
            message
            and path.choice_idx is not None
            and (stage := self.statistics_stages.get(path.choice_idx))
            is not None
        ):
            if (content := message.get("content")) is not None:
                stage.append_content(f"`{content or '∅'}`║")
                self.content_lengths[path.choice_idx] += len(content)
        return message

    def _collect_data_points(self, chunk: dict) -> None:
        self.response_end_time = time.time()

        for usage in collect_at_path(chunk, "statistics.usage_per_model.*"):
            self.usage_per_model.append(UsagePerModel.parse_obj(usage))

    def _get_choice_metrics(self, choice_idx: int) -> str:
        # NOTE: each metric but content_length and finish_reason
        # is shared across all choices.
        # So they will be repeated for each choice.

        metrics = MarkdownTable(headers=["Metric", "Value"])

        metrics.add_rows(
            ["Finish reason", self.finish_reasons.get(choice_idx) or "NA"],
            ["Prompt tokens", self.prompt_tokens],
            ["Completion tokens", self.completion_tokens],
        )

        response_duration = self.response_end_time - self.response_start_time
        latency = self.response_start_time - self.request_end_time

        metrics.add_rows(["Latency, sec", f"{latency:.2f}"])
        metrics.add_rows(["Stream duration, sec", f"{response_duration:.2f}"])

        if response_duration > 0:
            metrics.add_rows(
                [
                    "Chars/sec",
                    f"{self.content_lengths[choice_idx] / response_duration:.2f}",
                ],
                [
                    "Tokens/sec",
                    f"{self.completion_tokens / response_duration:.2f}",
                ],
            )

        usages = MarkdownTable(
            title="Per model usage",
            headers=["Idx", "Model", "Prompt tokens", "Completion tokens"],
        )

        for idx, usage in enumerate(self.usage_per_model, start=1):
            usages.add_row(
                [
                    idx,
                    usage.model,
                    usage.prompt_tokens,
                    usage.completion_tokens,
                ]
            )

        return "\n\n" + metrics.to_markdown() + usages.to_markdown_opt()

    @override
    async def on_request(self, request: dict) -> dict:
        self.request_end_time = time.time()
        self.request_n = request.get("n") or 1
        return request

    @override
    async def on_stream_start(self) -> None:
        # NOTE: one could create new stages inside `on_response_choice` callback.
        # However, this will affect the stage indices mapping in case if the
        # first chunk already contains stages. Those will be pinned and new stages
        # will come after them.
        # This is not what we want - we want these stages to *always* come first.
        for choice_idx in range(self.request_n):
            stage = Stage(
                self.response._queue,
                choice_idx,
                self.reserve_stage_index(choice_idx),
                "Statistics",
            )

            stage.open()
            stage.append_content("### Stream\n\n")
            self.statistics_stages[choice_idx] = stage

    @override
    async def on_stream_chunk(self, chunk: dict) -> None:
        if self.response_start_time == -1:
            self.response_start_time = time.time()

        self._collect_data_points(chunk)
        self.send_chunk(chunk)

    @override
    async def on_stream_end(self) -> None:
        for choice_idx in range(self.request_n):
            if stage := self.statistics_stages.get(choice_idx):
                stage.append_content(self._get_choice_metrics(choice_idx))
                stage.close()
