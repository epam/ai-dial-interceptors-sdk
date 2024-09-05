from collections import defaultdict
from typing import Dict, List

from aidial_sdk.chat_completion import Stage
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from aidial_interceptors_sdk.examples.interceptor.chat_completion.pii_anonymiser.spacy_anonymizer import (
    DEFAULT_LABELS_TO_REDACT,
    SpacyAnonymizer,
)
from aidial_interceptors_sdk.examples.utils.markdown import MarkdownTable
from aidial_interceptors_sdk.utils._env import get_env_list

PII_ANONYMIZER_LABELS_TO_REDACT = get_env_list(
    "PII_ANONYMIZER_LABELS_TO_REDACT", DEFAULT_LABELS_TO_REDACT
)


class PIIAnonymizerInterceptor(ChatCompletionInterceptor):
    anonymizer: SpacyAnonymizer = SpacyAnonymizer(
        labels_to_redact=PII_ANONYMIZER_LABELS_TO_REDACT
    )

    # Request data
    request_n: int = 0
    anonymized_request: str = ""

    # Per-choice response data
    original_response_stages: Dict[int, Stage] = {}
    content_buffers: Dict[int, str] = defaultdict(str)

    @override
    async def on_request_messages(self, messages: List[dict]) -> List[dict]:
        # Collect replacement dictionary first across all messages
        for message in messages:
            self.anonymizer.anonymize(message.get("content") or "")

        # Then apply the replacements
        if not self.anonymizer.is_empty():
            chat_table = MarkdownTable(
                title="Anonymized chat history", headers=["Role", "Content"]
            )

            for message in messages:
                if message.get("content"):
                    message["content"] = self.anonymizer.anonymize(
                        message["content"]
                    )

                    content = self.anonymizer.highlight_anonymized_entities(
                        message["content"]
                    )

                    role = (message["role"] or "").upper()
                    chat_table.add_row([role, content])

            self.anonymized_request += (
                chat_table.to_markdown()
                + self.anonymizer.replacements_to_markdown_table()
            )

        return messages

    @override
    async def on_request(self, request: dict) -> dict:
        self.request_n = request.get("n") or 1
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
    async def on_stream_chunk(self, chunk: dict) -> None:
        # NOTE: re-chunking invalidates streaming usage reported by the upstream model

        assert self.original_response_stages is not None

        for choice in chunk.get("choices") or []:
            choice_idx = choice.get("index") or 0

            content = (choice.get("delta") or {}).get("content") or ""
            finish_reason = choice.get("finish_reason")

            if content:
                self.original_response_stages[choice_idx].append_content(
                    content
                )

                buffer = self.content_buffers[choice_idx] + content

                br_open = buffer.count("[")
                br_closed = buffer.count("]")

                if br_open <= br_closed or finish_reason:
                    choice["delta"]["content"] = self.anonymizer.deanonymize(
                        buffer
                    )
                    buffer = ""
                else:
                    choice["delta"]["content"] = ""

                self.content_buffers[choice_idx] = buffer

        self.send_chunk(chunk)

    async def on_stream_end(self) -> None:
        for choice_idx in range(self.request_n):
            if stage := self.original_response_stages.get(choice_idx):
                if content := self.content_buffers[choice_idx]:
                    stage.append_content(content)
                stage.close()
