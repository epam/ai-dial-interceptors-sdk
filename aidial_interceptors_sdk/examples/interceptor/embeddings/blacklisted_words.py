from aidial_sdk.exceptions import invalid_request_error
from typing_extensions import override

from aidial_interceptors_sdk.embeddings.base import EmbeddingsInterceptor


class BlacklistedWordsInterceptor(EmbeddingsInterceptor):
    BLACKLIST = {"hello", "world"}

    @override
    async def modify_input(self, input: str) -> str:
        for word in self.BLACKLIST:
            if word.lower() in input.lower():
                message = "The embedding input contains a blacklisted word."
                raise invalid_request_error(
                    message=message,
                    display_message=message,
                )
        return input
