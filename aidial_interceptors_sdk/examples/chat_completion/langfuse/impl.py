from datetime import datetime
from typing import Optional

import httpx
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from aidial_interceptors_sdk.chat_completion.element_path import ElementPath
from aidial_interceptors_sdk.examples.chat_completion.langfuse.langfuse_client import (
    LangfuseClient,
)
from aidial_interceptors_sdk.examples.chat_completion.langfuse.session import (
    Session,
)
from aidial_interceptors_sdk.utils.not_given import NotGiven


class LangfuseInterceptor(ChatCompletionInterceptor):
    """
    Save data to Langfuse
    """

    session: Session = Session()
    user_email: str = ""
    request_deployment_id: str = ""
    request_model: str = ""
    response_content = ""
    response_custom_content = {}
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    x_conversation_id: str = ""
    is_model: bool = False
    model_info: Optional[dict]

    @override
    async def on_response_message(
        self, path: ElementPath, message: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        if message:
            message = self.session.add_session_id_to_message(message)
            self._update_response_content(message)
            self._update_response_custom_content(message)
        return message

    @override
    async def on_request(self, request: dict) -> dict:
        self.request_deployment_id = self.request.deployment_id or ""
        self.request_model = self.request.model or ""
        self.x_conversation_id = self.request.headers["x-conversation-id"]
        self.session.find_or_initialize(messages=request["messages"])
        request["messages"] = self.session.remove_session_id_from_messages(
            messages=request["messages"]
        )
        return request

    @override
    async def on_stream_start(self) -> None:
        self.start_time = datetime.now()

    @override
    async def on_stream_end(self) -> None:
        self.end_time = datetime.now()
        self.model_info = await self._get_model_info(
            self.dial_client.storage.api_key
        )
        self.user_email = await self._get_user_email(
            self.dial_client.storage.api_key
        )
        self.is_model = bool(self.model_info)
        tags = []
        if self.request_model:
            tags.append(self.request_model)
        if self.request_deployment_id:
            tags.append(self.request_deployment_id)
        LangfuseClient(
            session_id=self.session.session_id,
            tags=tags,
            request_messages=self.request.messages,
            response_message={
                "content": self.response_content,
                "custom_content": self.response_custom_content,
            },
            model_name=self.request_model,
            deployment_id=self.request_deployment_id,
            start_time=self.start_time or datetime.now(),
            end_time=self.end_time or datetime.now(),
            user_id=self.user_email,
            metadata={
                "model": self.request_model,
                "deployment_id": self.request_deployment_id,
                "x_conversation_id": self.x_conversation_id,
                "is_model": self.is_model,
                "model_info": self.model_info,
            },
            is_model=self.is_model,
        ).transmit()

    async def _get_user_email(self, api_key: str) -> str:
        client = httpx.AsyncClient(
            base_url=self.dial_client.dial_url, headers={"Api-Key": api_key}
        )
        response = await client.get("/v1/user/info")
        response.raise_for_status()
        return response.json().get("userClaims", {}).get("email", [""])[0]

    async def _get_model_info(self, api_key) -> dict | None:
        client = httpx.AsyncClient(
            base_url=self.dial_client.dial_url, headers={"Api-Key": api_key}
        )
        response = await client.get("/openai/models")
        response.raise_for_status()
        model_info = next(
            (
                item
                for item in response.json().get("data", [])
                if item["id"] == self.request_model
            ),
            None,
        )
        return model_info

    def _update_response_content(self, message: dict) -> None:
        if (content := message.get("content")) is not None:
            self.response_content += content

    def _update_response_custom_content(self, message: dict) -> None:
        if (custom_content := message.get("custom_content")) is not None:
            self.response_custom_content = self._merge_dicts(
                self.response_custom_content, custom_content
            )

    def _merge_dicts(self, dict1: dict, dict2: dict) -> dict:
        merged = dict1.copy()
        for key, value in dict2.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = self._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged
