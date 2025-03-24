from typing import List

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

    async def on_request_message(
        self, path: ElementPath, message: dict
    ) -> List[dict]:
        return [message]

    async def on_request_messages(self, messages: List[dict]) -> List[dict]:
        return messages

    async def on_request(self, request: dict) -> dict:
        return request

    async def traverse_request(self, r: dict) -> dict:
        async def traverse_message(
            path: ElementPath, message: dict
        ) -> List[dict]:
            message = await self.traverse_request_message(path, message)
            return await self.on_request_message(path, message)

        async def traverse_messages(
            path: ElementPath, messages: List[dict]
        ) -> List[dict]:
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
