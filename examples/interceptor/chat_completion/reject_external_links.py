from typing import List
from urllib.parse import urljoin

from aidial_sdk.exceptions import invalid_request_error
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)


class RejectExternalLinksInterceptor(ChatCompletionInterceptor):
    @override
    async def on_request_attachment(self, path, attachment: dict) -> List[dict]:
        url = attachment.get("url")
        if url is None:
            return [attachment]

        dial_url = self.dial_client.dial_url
        abs_url = urljoin(dial_url, url)
        if not abs_url.startswith(dial_url):
            message = f"External links are not allowed: {url!r}"
            raise invalid_request_error(
                message=message,
                display_message=message,
            )

        return [attachment]
