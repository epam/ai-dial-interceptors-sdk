from typing import Type

import httpx
import openai
import pytest
from pydantic import BaseModel

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from tests.utils.applications import EchoApplication
from tests.utils.dial_app import create_openai_client


class RequiredConf(BaseModel):
    name: str
    count: int


class OptionalConf(BaseModel):
    name: str = "abc"
    count: int = 42


@pytest.fixture(params=[False, True])
def stream(request):
    return request.param


def create_configurable_interceptor(
    conf_cls: Type[BaseModel] | None,
) -> Type[ChatCompletionInterceptor]:
    class _Impl(ChatCompletionInterceptor):
        @classmethod
        async def configuration_schema(cls):
            return conf_cls

        async def on_stream_start(self) -> None:
            if conf_cls is None:
                config = "null"
            else:
                config = self.get_configuration(conf_cls).json()
            raise ValueError(config)

    return _Impl


def test_configuration_and_no_schema(stream: bool):
    intr = create_configurable_interceptor(conf_cls=None)
    openai_client = create_openai_client(
        [("echo", EchoApplication()), ("intr", intr)],
        ["intr", "echo"],
    )

    with pytest.raises(openai.UnprocessableEntityError) as exc:
        openai_client.chat.completions.create(
            model=None,  # type: ignore
            stream=stream,
            messages=[{"role": "user", "content": "hello"}],
            extra_body={
                "custom_fields": {"interceptor_configuration": "whatever"}
            },
        )

    assert exc.value.response.json() == {
        "error": {
            "code": "422",
            "message": "The interceptor doesn't have configuration, but it was provided in the chat completion request",
            "type": "invalid_request_error",
        }
    }


def test_no_configuration_and_no_schema(stream: bool):
    intr = create_configurable_interceptor(conf_cls=None)
    openai_client = create_openai_client(
        [("echo", EchoApplication()), ("intr", intr)],
        ["intr", "echo"],
    )

    with pytest.raises(openai.InternalServerError) as exc:
        openai_client.chat.completions.create(
            model=None,  # type: ignore
            stream=stream,
            messages=[{"role": "user", "content": "hello"}],
        )

    assert exc.value.response.json() == {
        "error": {
            "message": "null",
            "type": "internal_server_error",
            "code": "500",
        }
    }


def test_no_configuration_and_optional_schema(stream: bool):
    intr = create_configurable_interceptor(conf_cls=OptionalConf)
    openai_client = create_openai_client(
        [("echo", EchoApplication()), ("intr", intr)],
        ["intr", "echo"],
    )

    with pytest.raises(openai.InternalServerError) as exc:
        openai_client.chat.completions.create(
            model=None,  # type: ignore
            stream=stream,
            messages=[{"role": "user", "content": "hello"}],
        )

    assert exc.value.response.json() == {
        "error": {
            "message": OptionalConf().json(),
            "type": "internal_server_error",
            "code": "500",
        }
    }


def test_no_configuration_and_required_schema(stream: bool):
    intr = create_configurable_interceptor(conf_cls=RequiredConf)
    openai_client = create_openai_client(
        [("echo", EchoApplication()), ("intr", intr)],
        ["intr", "echo"],
    )

    with pytest.raises(openai.UnprocessableEntityError) as exc:
        openai_client.chat.completions.create(
            model=None,  # type: ignore
            stream=stream,
            messages=[{"role": "user", "content": "hello"}],
        )

    assert exc.value.response.json() == {
        "error": {
            "message": "Invalid request. Path: 'custom_fields.interceptor_configuration.name', error: field required",
            "type": "invalid_request_error",
            "code": "422",
        }
    }


def test_configuration_and_required_schema(stream: bool):
    intr = create_configurable_interceptor(conf_cls=RequiredConf)
    openai_client = create_openai_client(
        [("echo", EchoApplication()), ("intr", intr)],
        ["intr", "echo"],
    )

    with pytest.raises(openai.InternalServerError) as exc:
        openai_client.chat.completions.create(
            model=None,  # type: ignore
            stream=stream,
            messages=[{"role": "user", "content": "hello"}],
            extra_body={
                "custom_fields": {
                    "interceptor_configuration": {
                        "name": "xyz",
                        "count": 111,
                        "extra_field": "extra_value",
                    }
                }
            },
        )

    assert exc.value.response.json() == {
        "error": {
            "message": '{"name": "xyz", "count": 111}',
            "type": "internal_server_error",
            "code": "500",
        }
    }


def test_configuration_endpoint_implemented():
    intr = create_configurable_interceptor(conf_cls=RequiredConf)
    openai_client = create_openai_client([("intr", intr)], ["intr"])

    response = openai_client.get(path="/configuration", cast_to=httpx.Response)

    assert response.json() == {
        "title": "RequiredConf",
        "type": "object",
        "properties": {
            "name": {"title": "Name", "type": "string"},
            "count": {"title": "Count", "type": "integer"},
        },
        "required": ["name", "count"],
    }


def test_configuration_endpoint_not_implemented():
    intr = create_configurable_interceptor(conf_cls=None)
    openai_client = create_openai_client([("intr", intr)], ["intr"])

    with pytest.raises(openai.NotFoundError) as exc:
        openai_client.get(path="/configuration", cast_to=httpx.Response)

    assert exc.value.status_code == 404
    assert exc.value.response.json() == {
        "error": {
            "code": "404",
            "message": "Configuration endpoint isn't implemented",
            "type": "runtime_error",
        }
    }
