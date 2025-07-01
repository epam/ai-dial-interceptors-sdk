from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List

from aidial_sdk.chat_completion import Stage
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from aidial_interceptors_sdk.chat_completion.element_path import ElementPath
from aidial_interceptors_sdk.examples.utils.markdown import MarkdownTable

from .base import Anonymizer
from .replacements import Replacements


class AnonymizerInterceptor(ChatCompletionInterceptor, ABC):

    # Request data
    request_n: int = 0
    anonymized_request: str = ""

    # Per-choice response data
    original_response_stages: Dict[int, Stage] = {}
    content_buffers: Dict[int, str] = defaultdict(str)

    replacements: Replacements = Replacements()

    @abstractmethod
    def get_anonymizer(self, config: dict) -> Anonymizer:
        pass

    @abstractmethod
    def get_anonymizer_config_field_name(self) -> str | None:
        pass

    @override
    async def on_request_messages(self, messages: List[dict]) -> List[dict]:
        request = await self.request.original_request.json()
        config = self._get_interceptor_configuration(request, clean_up=False)

        # Collect replacement dictionary first across all messages
        anonymizer = self.get_anonymizer(config)
        for message in messages:
            await anonymizer.collect_replacements(
                message.get("content") or "", replacements=self.replacements
            )

        # Then apply the replacements
        if not self.replacements.is_empty():
            chat_table = MarkdownTable(
                title="Anonymized chat history",
                headers=["Role", "Content"],
            )

            for message in messages:
                if message.get("content"):
                    message["content"] = self.replacements.anonymize(
                        message["content"]
                    )

                    content = self.replacements.highlight_anonymized_entities(
                        message["content"]
                    )

                    role = (message["role"] or "").upper()
                    chat_table.add_row([role, content])

            self.anonymized_request += (
                chat_table.to_markdown() + self.replacements.to_markdown_table()
            )

        return messages

    def _get_interceptor_configuration(
        self, request: dict, *, clean_up: bool
    ) -> dict:
        field_name = self.get_anonymizer_config_field_name()

        if (
            field_name
            and (cc := request.get("custom_fields"))
            and (config := cc.get("configuration"))
            and (conf := config.get(field_name))
        ):
            if clean_up:
                # Remove interceptor's configuration from the request.
                # It must not reach the upstream, it won't understand it.
                del config[field_name]
            return conf

        return {}

    @override
    async def on_request(self, request: dict) -> dict:
        self.request_n = request.get("n") or 1
        self._get_interceptor_configuration(request, clean_up=True)
        return request

    @override
    async def on_stream_start(self) -> None:
        for choice_idx in range(self.request_n):
            with Stage(
                self.response._queue,
                choice_idx,
                self.reserve_stage_index(choice_idx),
                "Anonymized request",
            ) as stage:
                stage.append_content(self.anonymized_request)

            self.original_response_stages[choice_idx] = Stage(
                self.response._queue,
                choice_idx,
                self.reserve_stage_index(choice_idx),
                "Original response",
            )
            self.original_response_stages[choice_idx].open()

    @override
    async def on_response_choice(
        self, path: ElementPath, choice: Dict
    ) -> List[Dict] | Dict:
        # NOTE: re-chunking invalidates streaming usage reported by the upstream model
        choice_idx = path.choice_idx
        assert choice_idx is not None

        if content := (choice.get("delta") or {}).get("content") or "":
            self.original_response_stages[choice_idx].append_content(content)

            buffer: str = self.content_buffers[choice_idx] + content

            br_open = buffer.count("[")
            br_closed = buffer.count("]")

            if br_open <= br_closed or choice.get("finish_reason"):
                choice["delta"]["content"] = self.replacements.deanonymize(
                    buffer
                )
                buffer = ""
            else:
                choice["delta"]["content"] = ""

            self.content_buffers[choice_idx] = buffer

        return choice

    async def on_stream_end(self) -> None:
        for choice_idx in range(self.request_n):
            if stage := self.original_response_stages.get(choice_idx):
                if content := self.content_buffers[choice_idx]:
                    stage.append_content(content)
                stage.close()
