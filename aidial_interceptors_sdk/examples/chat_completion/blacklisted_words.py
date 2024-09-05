from typing import List

from aidial_sdk.exceptions import InvalidRequestError
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from aidial_interceptors_sdk.utils.not_given import NotGiven


class BlacklistedWordsInterceptor(ChatCompletionInterceptor):
    BLACKLIST = {"hello", "world"}

    total_content: str = ""

    def _validate_content_in(self, entity: str, content: str):
        for word in self.BLACKLIST:
            if word.lower() in content.lower():
                error_message = (
                    f"The chat completion {entity} contains a blacklisted word."
                )
                raise InvalidRequestError(
                    message=error_message,
                    display_message=error_message,
                )

    @override
    async def on_request_message(self, path, message: dict) -> List[dict]:
        content = message.get("content") or ""
        self._validate_content_in("request", content)
        return [message]

    @override
    async def on_response_message(
        self, path, message: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        if isinstance(message, dict):
            content = message.get("content") or ""
            self.total_content += content
            self._validate_content_in("response", self.total_content)
        return message
