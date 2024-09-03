import fastapi
import pytest
from aidial_sdk.chat_completion import Request, Response
from aidial_sdk.pydantic_v1 import SecretStr
from aidial_sdk.utils.streaming import merge_chunks

from aidial_interceptors_sdk.chat_completion.annotated_chunk import (
    AnnotatedChunk,
)
from aidial_interceptors_sdk.chat_completion.element_path import ElementPath
from aidial_interceptors_sdk.chat_completion.response_handler import (
    ResponseHandler,
)
from aidial_interceptors_sdk.utils.not_given import NOT_GIVEN, NotGiven

RESPONSE_CHUNK = {
    "id": "chatcmpl-123",
    "object": "chat.completion,chunk",
    "created": 1677652288,
    "model": "gpt-4o-mini",
    "system_fingerprint": "fp_44709d6fcb",
    "choices": [
        {
            "index": 0,
            "delta": {
                "role": "assistant",
                "content": "assistant response",
                "custom_content": {
                    "attachments": [{}, {}],
                    "stages": [
                        {
                            "index": 0,
                            "name": "Stage name",
                            "content": "hello",
                            "attachments": [{"title": "Attachment title"}],
                        }
                    ],
                },
            },
            "logprobs": None,
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 9,
        "completion_tokens": 12,
        "total_tokens": 21,
    },
}


async def get_response(cls: type[ResponseHandler], **kwargs) -> dict:
    dummy_request = Request(
        messages=[],
        stream=False,
        api_key_secret=SecretStr("dummy"),
        deployment_id="dummy",
        headers={},
        original_request=fastapi.Request(scope={"type": "http"}),
        **kwargs
    )

    response = Response(request=dummy_request)

    async def producer(request: Request, response: Response):
        handler = cls(response=response)
        ann_chunk = AnnotatedChunk(chunk=RESPONSE_CHUNK)
        await handler.traverse_response_chunk(ann_chunk)

    first_chunk = await response._generator(producer, dummy_request)
    return await merge_chunks(response._generate_stream(first_chunk))


# Test 1: Add a second choice, which is same as the first one, but with index=1
class AddSecondChoice(ResponseHandler):
    async def on_response_choice(self, path: ElementPath, choice: dict):
        return [choice, {**choice, "index": 1}]


@pytest.mark.asyncio
async def test_add_second_choice():
    response = await get_response(AddSecondChoice, n=2)
    assert len(response["choices"]) == 2
    assert response["choices"][1]["index"] == 1


# Test 2: Remove all attachments in the message returning NOT_GIVEN
class RemoveAttachmentsNotGiven(ResponseHandler):
    async def on_response_attachments(self, path: ElementPath, attachments):
        return NOT_GIVEN


@pytest.mark.asyncio
async def test_remove_attachments_not_given():
    response = await get_response(RemoveAttachmentsNotGiven)
    assert (
        "attachments" not in response["choices"][0]["message"]["custom_content"]
    )


# Test 3: Remove all attachments in the message by returning None
class RemoveAttachmentsNone(ResponseHandler):
    async def on_response_attachments(self, path: ElementPath, attachments):
        return None


@pytest.mark.asyncio
async def test_remove_attachments_none():
    response = await get_response(RemoveAttachmentsNone)
    assert (
        response["choices"][0]["message"]["custom_content"]["attachments"]
        is None
    )


# Test 4: Set the title of the first stage attachment to "New title"
class SetStageAttachmentTitle(ResponseHandler):
    async def on_response_attachment(self, path: ElementPath, attachment):
        if path.attachment_idx == 0 and path.stage_idx == 0:
            return [{**attachment, "title": "New " + attachment["title"]}]
        return [attachment]


@pytest.mark.asyncio
async def test_set_stage_attachment_title():
    response = await get_response(SetStageAttachmentTitle)
    assert (
        response["choices"][0]["message"]["custom_content"]["stages"][0][
            "attachments"
        ][0]["title"]
        == "New Attachment title"
    )


# Test 5: Multiply usage numbers by 2
class MultiplyUsageNumbers(ResponseHandler):
    async def on_response_usage(self, usage: dict | NotGiven | None):
        if usage:
            usage["prompt_tokens"] *= 2
            usage["completion_tokens"] *= 2
            usage["total_tokens"] *= 2
        return usage


@pytest.mark.asyncio
async def test_multiply_usage_numbers():
    response = await get_response(MultiplyUsageNumbers)
    assert response["usage"]["prompt_tokens"] == 18
    assert response["usage"]["completion_tokens"] == 24
    assert response["usage"]["total_tokens"] == 42


# Test 6: Add a state equals to "{'status': 'done'}"
class AddState(ResponseHandler):
    async def on_response_state(self, path: ElementPath, state):
        return {"status": "done"}


@pytest.mark.asyncio
async def test_add_state():
    response = await get_response(AddState)
    assert response["choices"][0]["message"]["custom_content"]["state"] == {
        "status": "done"
    }
