from aidial_sdk.chat_completion import Request

from aidial_interceptors_sdk.chat_completion.element_path import ElementPath
from aidial_interceptors_sdk.chat_completion.helpers import (
    traverse_list,
    traverse_required_dict_value,
)
from aidial_interceptors_sdk.chat_completion.request_message_handler import (
    RequestMessageHandler,
)


class RequestHandler(RequestMessageHandler):
    request: Request

    @property
    def upstream_deployment_id(self) -> str | None:
        """
        Since ai-dial-core 0.43.0 returns ID of a DIAL deployment that
        this interceptor is assigned to.

        Not to be confused with the following values:

        1. self.request.deployment_id - the deployment ID of the interceptor itself.
            Populated from the `deployment_id` path variable in the endpoint that interceptor service is exposing:
            * POST /openai/deployments/{deployment_id}/chat/completions
            * POST /openai/deployments/{deployment_id}/embeddings

        2. self.request.model - the `model` field of the incoming Chat Completions request.
            There is no guarantee that it reflects an actual DIAL deployment ID.
        """
        return self.request.headers.get("X-DIAL-DEPLOYMENT-ID")

    async def on_request_message(
        self, path: ElementPath, message: dict
    ) -> list[dict]:
        return [message]

    async def on_request_messages(self, messages: list[dict]) -> list[dict]:
        return messages

    async def on_request(self, request: dict) -> dict:
        return request

    async def traverse_request(self, r: dict) -> dict:
        async def traverse_message(
            path: ElementPath, message: dict
        ) -> list[dict]:
            message = await self.traverse_request_message(path, message)
            return await self.on_request_message(path, message)

        async def traverse_messages(
            path: ElementPath, messages: list[dict]
        ) -> list[dict]:
            messages = await traverse_list(
                path.with_message_idx, messages, traverse_message
            )
            return await self.on_request_messages(messages)

        path = ElementPath()
        r = await traverse_required_dict_value(
            path, r, "messages", traverse_messages
        )
        r = await self.on_request(r)

        return r
