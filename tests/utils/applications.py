from aidial_sdk.chat_completion import ChatCompletion, Request, Response


class EchoApplication(ChatCompletion):
    async def chat_completion(
        self, request: Request, response: Response
    ) -> None:
        with response.create_single_choice() as choice:
            choice.append_content(request.messages[-1].text())
