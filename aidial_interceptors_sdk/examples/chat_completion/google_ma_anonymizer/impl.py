import base64
import os
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote

from aidial_sdk.chat_completion import Stage
from aidial_sdk.chat_completion.chunks import ContentChunk
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion import ChatCompletionInterceptor
from aidial_interceptors_sdk.chat_completion.element_path import ElementPath
from aidial_interceptors_sdk.utils._env import get_env

from .anonymizer import GCPModelArmorPromptsGuard
from .transform_utils import transform_to_table_by_schema


class GoogleModelArmorAnonymizerInterceptor(ChatCompletionInterceptor):
    request_n: int = 0
    anonymized_request: str = ""
    full_response: str = ""

    original_response_stages: Dict[int, Stage] = {}
    content_buffers: Dict[int, str] = defaultdict(str)
    guard: GCPModelArmorPromptsGuard = None

    def _init(self):
        project = get_env("GOOGLE_PROJECT")
        region = get_env("GOOGLE_REGION")
        inspect_template = get_env("GOOGLE_INSPECT_TEMPLATE")
        deidentify_template = get_env("GOOGLE_DEIDENTIFY_TEMPLATE")
        kms_key_name = get_env("GOOGLE_KMS_KEY_NAME")
        wrapped_key = base64.b64decode(get_env("GOOGLE_KMS_WRAPPED_KEY"))
        key_file = get_env("GOOGLE_APPLICATION_CREDENTIALS")
        surrogate_info_type = get_env("GOOGLE_SURROGATE_INFO_TYPE")
        return {
            "project": project,
            "region": region,
            "inspect_template": inspect_template,
            "deidentify_template": deidentify_template,
            "kms_key_name": kms_key_name,
            "wrapped_key": wrapped_key,
            "key_file": key_file,
            "surrogate_info_type": surrogate_info_type,
        }

    @override
    async def on_response_message(self, path, message: dict) -> list[dict]:
        c = message.get("content")
        if c:
            self.full_response += c

        return [message]

    @override
    async def on_request_message(
        self, path: str, message: dict
    ) -> Dict[str, List[dict]]:

        schema = ["text", "infoType", "obfuscated"]
        tables: List[str] = []
        content_blocks: List[Dict] = []

        attachment = message.get("custom_content", {}).get("attachments", [{}])[
            0
        ]
        if url := attachment.get("url"):
            binary: bytes = await self.dial_client.storage.download(url)

            # de-identify the image with Model Armor / your guard service
            result = await self._guard_instance().deidentify_image(
                os.path.basename(unquote(url)), binary
            )

            if result:
                findings, image_b64 = self._split_findings_and_data(result)
                tables.append(transform_to_table_by_schema(findings, schema))

                mime = attachment.get("type", "image/png")  # default MIME
                data_uri = f"data:{mime};base64,{image_b64}"
                content_blocks.append(
                    {"type": "image_url", "image_url": {"url": data_uri}}
                )

        raw_text = message.get("content", "")
        pii_matches = await self._guard_instance().get_sensitive_fields(
            raw_text
        )

        if pii_matches:
            redacted = await self._guard_instance().deidentify(raw_text)

            # map each match → its PII_TOKEN replacement
            tokens = re.findall(
                r"PII_TOKEN(?:\(\d+\))?:[A-Za-z0-9+/=]+", redacted
            )
            for match_dict, token in zip(pii_matches, tokens):
                match_dict["obfuscated"] = token

            tables.append(transform_to_table_by_schema(pii_matches, schema))
            text_to_send = redacted
        else:
            text_to_send = raw_text

        # push (redacted) text ahead of images for better model context
        content_blocks.insert(0, {"type": "text", "text": text_to_send})

        if tables:
            self.anonymized_request = "\n\n-----\n\n".join(tables)
        ret = {"role": "user", "content": content_blocks}
        return ret

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
                "sensitive",
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
        choice_idx = path.choice_idx
        assert choice_idx is not None
        delta_list = choice.get("delta", [])
        if delta_list and isinstance(delta_list[0], dict):
            content = delta_list[0].get("content", "")
        else:
            content = ""
        if content:
            self.original_response_stages[choice_idx].append_content(content)
            buffer: str = self.content_buffers[choice_idx] + content
            br_open = buffer.count("[")
            br_closed = buffer.count("]")
            if br_open <= br_closed or choice.get("finish_reason"):
                delta_list[0]["content"] = buffer
                buffer = ""
            else:
                delta_list[0]["content"] = ""
            self.content_buffers[choice_idx] = buffer

        return choice

    async def on_stream_end(self) -> None:
        for choice_idx in range(self.request_n):
            if stage := self.original_response_stages.get(choice_idx):
                if content := self.content_buffers[choice_idx]:
                    stage.append_content(content)
                stage.close()
        self.full_response = await self._guard_instance().reidentify(
            self.full_response
        )
        self.send_chunk(ContentChunk(self.full_response, 0))
        self.full_response = ""

    def _guard_instance(self) -> GCPModelArmorPromptsGuard:
        if self.guard is None:
            params = self._init()
            self.guard = GCPModelArmorPromptsGuard(**params)

        return self.guard

    def _split_findings_and_data(
        self, items: List[Dict]
    ) -> Tuple[List[Dict], Optional[str]]:

        if not items:
            return [], None

        if len(items) and set(items[-1].keys()) == {"data"}:
            b64_str = items[-1]["data"]
            findings = items[:-1]
            return findings, b64_str

        if "data" in items[0]:
            b64_str = items[0]["data"]
            findings = [
                {k: v for k, v in f.items() if k != "data"} for f in items
            ]
            return findings, b64_str

        return items, None
