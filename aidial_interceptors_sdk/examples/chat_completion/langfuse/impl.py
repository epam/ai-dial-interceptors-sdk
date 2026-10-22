import httpx
from aidial_sdk.utils.merge_chunks import merge
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.annotated_value import (
    AnnotatedException,
)
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
    request_deployment_id: str = ""
    request_model: str = ""
    merged_response_message = {}
    x_conversation_id: str = ""
    langfuse_client: LangfuseClient | None = None

    @override
    async def on_response_message(
        self, path: ElementPath, message: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        if message:
            message = self.session.add_session_id_to_message(message)
            self.merged_response_message = merge(
                self.merged_response_message, message
            )
        return message

    @override
    async def on_request(self, request: dict) -> dict:
        self.request_deployment_id = self.request.deployment_id or ""
        self.request_model = self.request.model or ""
        self.x_conversation_id = self.request.headers["x-conversation-id"]
        self.session = Session.create(messages=request["messages"])
        request["messages"] = self.session.remove_session_id_from_messages(
            messages=request["messages"]
        )
        return request

    @override
    async def on_stream_start(self) -> None:
        # The observation is opened here, rather than when the stream ends,
        # so that the interval it reports is the real span of the stream.
        model_info = await self._get_model_info()
        user_email = await self._get_user_email()
        is_model = bool(model_info)
        tags = []
        if self.request_model:
            tags.append(self.request_model)
        if self.request_deployment_id:
            tags.append(self.request_deployment_id)
        self.langfuse_client = LangfuseClient(
            session_id=self.session.session_id,
            tags=tags,
            request_messages=self.request.messages,
            model_name=self.request_model,
            deployment_id=self.request_deployment_id,
            user_id=user_email,
            metadata={
                "model": self.request_model,
                "deployment_id": self.request_deployment_id,
                "x_conversation_id": self.x_conversation_id,
                "is_model": is_model,
                "model_info": model_info,
            },
            is_model=is_model,
        )
        self.langfuse_client.start()

    @override
    async def on_stream_end(self) -> None:
        if self.langfuse_client:
            self.langfuse_client.finish(self.merged_response_message)

    @override
    async def on_stream_error(self, error: AnnotatedException) -> None:
        # Close the observation the failed stream left open, then let the
        # error through as the base interceptor does.
        if self.langfuse_client:
            self.langfuse_client.finish(self.merged_response_message)
        await super().on_stream_error(error)

    async def _get_user_email(self) -> str:
        response = await self._get_dial_client().get("/v1/user/info")
        response.raise_for_status()
        return response.json().get("userClaims", {}).get("email", [""])[0]

    async def _get_model_info(self) -> dict | None:
        response = await self._get_dial_client().get("/openai/models")
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

    def _get_dial_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.dial_client.dial_url,
            headers={"Api-Key": self.dial_client.storage.api_key},
        )
