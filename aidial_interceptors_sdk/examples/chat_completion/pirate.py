from typing import List

from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)


class PirateInterceptor(ChatCompletionInterceptor):
    @override
    async def on_request_messages(self, messages: List[dict]) -> List[dict]:
        instruction = "Reply as a pirate."
        if len(messages) > 0 and messages[0]["role"] == "system":
            messages[0]["content"] = messages[0]["content"] + f"\n{instruction}"
            return messages
        else:
            return [{"role": "system", "content": instruction}, *messages]
