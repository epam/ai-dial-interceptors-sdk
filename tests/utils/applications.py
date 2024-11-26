from aidial_sdk.chat_completion import ChatCompletion, Request, Response
from aidial_sdk.exceptions import HTTPException as DialException
from fastapi.requests import Request as FastAPIRequest
from fastapi.responses import StreamingResponse as FastAPIStreamingResponse

from tests.utils.chunks import create_chunk, format_chunk


class EchoApplication(ChatCompletion):
    async def chat_completion(
        self, request: Request, response: Response
    ) -> None:
        with response.create_single_choice() as choice:
            choice.append_content(request.messages[-1].text())


def create_broken_application(error: DialException):
    async def _handler(request: FastAPIRequest):
        req = await request.json()
        stream = bool(req.get("stream"))

        if stream:

            def _gen():
                # FIXME: Due to a bug in DIAL SDK we could not simply
                # return an error as a first chunk.
                # A valid chunk should be generated first,
                # otherwise, SDK throws "Not all choices were generated" error.
                # This could be fixed by converting error chunks
                # into DIAL Exceptions in the Interceptors SDK instead of
                # treating them as normal chat completion chunks.
                # See `handle_streaming_errors`.
                yield format_chunk(create_chunk(stream=stream))
                yield format_chunk(error.json_error())
                yield format_chunk("[DONE]")

            return FastAPIStreamingResponse(_gen())
        else:
            return error.to_fastapi_response()

    return _handler
