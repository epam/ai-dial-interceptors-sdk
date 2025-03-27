import uuid
import requests
from datetime import datetime
from typing import Optional
from typing_extensions import override
from aidial_interceptors_sdk.chat_completion.base import ChatCompletionInterceptor
from aidial_interceptors_sdk.chat_completion.element_path import ElementPath
from aidial_interceptors_sdk.utils.not_given import NotGiven
from aidial_interceptors_sdk.utils._env import get_env
from aidial_interceptors_sdk.examples.chat_completion.langfuse.langfuse_client import LangfuseClient


class State:
    SESSION_ID_KEY = "langfuse_session_id"


class LangfuseInterceptor(ChatCompletionInterceptor):
    """
    Save data to Langfuse
    """

    session_id: str = ""
    user_email: str = ""
    request_deployment_id: str = ""
    request_model: str = ""
    response_message = {
        "content": "",
        "custom_content": {"state": [{State.SESSION_ID_KEY: None}]},
    }
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    x_conversation_id: str = ""
    is_model: bool = False
    model_info: dict = {}
    langfuse_secret_key: str = get_env("LANGFUSE_SECRET_KEY")
    langfuse_public_key: str = get_env("LANGFUSE_PUBLIC_KEY")
    langfuse_host: str = get_env("LANGFUSE_HOST")

    @override
    async def on_response_message(
        self, path: ElementPath, message: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        if message:
            message = self._set_session_id(message)
            self._update_response_message(message)
        return message

    @override
    async def on_request(self, request: dict) -> dict:
        self.request_deployment_id = self.request.deployment_id or ""
        self.request_model = self.request.model or ""
        self.x_conversation_id = self.request.headers["x-conversation-id"]
        self._get_session_id(messages=request["messages"])
        request["messages"] = self._remove_session_from_messages(
            messages=request["messages"]
        )
        return request

    @override
    async def on_stream_start(self) -> None:
        self.start_time = datetime.now()

    @override
    async def on_stream_end(self) -> None:
        self.end_time = datetime.now()
        self._get_model_info(self.dial_client.storage.api_key)
        self._get_user_email(self.dial_client.storage.api_key)
        LangfuseClient(
            session_id=self.session_id,
            tags=[
                str(self.request_model),
                str(self.request_deployment_id),
            ],
            request_messages=self.request.messages,
            response_message=self.response_message,
            model_name=self.request_model,
            deployment_id=self.request_deployment_id,
            start_time=self.start_time or datetime.now(),
            end_time=self.end_time or datetime.now(),
            user_id=self.user_email,
            langfuse_secret_key=self.langfuse_secret_key,
            langfuse_public_key=self.langfuse_public_key,
            langfuse_host=self.langfuse_host,
            metadata={
                "model": self.request_model,
                "deployment_id": self.request_deployment_id,
                "x_conversation_id": self.x_conversation_id,
                "is_model": self.is_model,
                "model_info": self.model_info,
            },
            is_model=self.is_model,
        ).transmit()

    def _get_user_email(self, api_key) -> None:
        url = f"{self.dial_client.dial_url}/v1/user/info"
        headers = {"Api-Key": api_key}
        response = requests.get(url, headers=headers)
        response_json = response.json()
        email = response_json.get("userClaims", {}).get("email", [None])[0]
        self.user_email = email
        return None

    def _get_model_info(self, api_key) -> None:
        url = f"{self.dial_client.dial_url}/openai/models"
        headers = {"Api-Key": api_key}
        response = requests.get(url, headers=headers)
        response_json = response.json()
        model_info = next(
            (
                item
                for item in response_json.get("data", [])
                if item["id"] == self.request_model
            ),
            None,
        )
        if model_info:
            self.is_model = True
            self.model_info = model_info
        return None

    def _get_session_id(self, messages: list[dict]) -> None:
        messages = list(
            filter(
                lambda msg: msg.get("custom_content")
                and msg["custom_content"].get("state")
                and State.SESSION_ID_KEY in msg["custom_content"]["state"][0],
                messages,
            )
        )
        if len(messages) > 0:
            self.session_id = messages[0]["custom_content"]["state"][0][
                State.SESSION_ID_KEY
            ]
        else:
            self.session_id = str(uuid.uuid4())

    def _set_session_id(self, message: dict) -> dict:
        if (
            self.response_message["custom_content"]["state"][0][State.SESSION_ID_KEY]
            is None
        ):
            message["custom_content"] = {
                "state": [{State.SESSION_ID_KEY: self.session_id}]
            }
            self.response_message["custom_content"]["state"][0][
                State.SESSION_ID_KEY
            ] = self.session_id
        return message

    def _remove_session_from_messages(self, messages: list[dict]) -> list[dict]:
        new_messages = []
        for message in messages:
            if (
                message.get("custom_content", {})
                .get("state", [{}])[0]
                .get(State.SESSION_ID_KEY)
            ):
                del message["custom_content"]["state"][0][State.SESSION_ID_KEY]
            if message.get("custom_content", {}).get("state") == [{}]:
                del message["custom_content"]
            new_messages.append(message)
        return new_messages

    def _update_response_message(self, message: dict) -> None:
        if (content := message.get("content")) is not None:
            self.response_message["content"] += content
