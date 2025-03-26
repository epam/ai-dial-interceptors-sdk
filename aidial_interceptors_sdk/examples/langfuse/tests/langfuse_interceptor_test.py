import uuid
import pytest
from datetime import datetime
from openai import AsyncAzureOpenAI
from unittest.mock import AsyncMock, MagicMock, patch
from ai_dial_interceptors_langfuse.config import Config, LangfuseConfig
from ai_dial_interceptors_langfuse.langfuse_interceptor import (
    LangfuseInterceptor,
    State,
)
from aidial_sdk.chat_completion import Request, Response
from aidial_interceptors_sdk.chat_completion.element_path import ElementPath
from aidial_interceptors_sdk.dial_client import DialClient
from aidial_interceptors_sdk.utils.storage import FileStorage


@pytest.fixture
def mock_dial_client():
    mock_client = AsyncMock(spec=AsyncAzureOpenAI)
    mock_storage = AsyncMock(spec=FileStorage)
    return DialClient(
        dial_url="http://example.com", client=mock_client, storage=mock_storage
    )


@pytest.fixture
def mock_request():
    mock_request = AsyncMock(spec=Request)
    mock_request.deployment_id = "deployment_123"
    mock_request.model = "gpt-4"
    mock_request.messages = []
    return mock_request


@pytest.fixture
def mock_response(mock_request):
    mock_response = AsyncMock(spec=Response)
    mock_response.request = mock_request
    return mock_response


@pytest.fixture
def mock_config():
    langfuse_config = LangfuseConfig.model_validate(
        {
            "secret_key": "secret_key",
            "public_key": "public_key",
            "host": "host",
        }
    )
    config = Config.model_validate(
        {"track_user_data": False, "langfuse": langfuse_config}
    )
    return config


@pytest.fixture
def interceptor(
    mock_dial_client: DialClient,
    mock_request: AsyncMock,
    mock_response: AsyncMock,
    mock_config: Config,
):
    return LangfuseInterceptor(
        dial_client=mock_dial_client,
        request=mock_request,
        response=mock_response,
        session_id="test-session-id",
        config=mock_config,
        start_time=None,
        end_time=None,
    )


@pytest.fixture
def fixed_uuid():
    with patch(
        "uuid.uuid4", return_value=uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")
    ):
        yield


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message_income, message_expected, response_message_before, response_message_expected, session_id",
    [
        (
            {"content": "2"},
            {
                "content": "2",
                "custom_content": {"state": [{State.SESSION_ID_KEY: "session_id_key"}]},
            },
            {
                "content": "1",
                "custom_content": {"state": [{State.SESSION_ID_KEY: None}]},
            },
            {
                "content": "12",
                "custom_content": {"state": [{State.SESSION_ID_KEY: "session_id_key"}]},
            },
            "session_id_key",
        ),
        (
            {"content": "2"},
            {"content": "2"},
            {
                "content": "1",
                "custom_content": {"state": [{State.SESSION_ID_KEY: "session_id_key"}]},
            },
            {
                "content": "12",
                "custom_content": {"state": [{State.SESSION_ID_KEY: "session_id_key"}]},
            },
            "session_id_key",
        ),
    ],
)
async def test_on_response_message(
    interceptor,
    message_income,
    message_expected,
    response_message_before,
    response_message_expected,
    session_id,
):
    interceptor.response_message = response_message_before
    interceptor.session_id = session_id
    updated_message = await interceptor.on_response_message(
        path=ElementPath(), message=message_income
    )
    assert updated_message == message_expected
    assert response_message_expected == interceptor.response_message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_income, request_expected, session_id_expected",
    [
        (
            {"messages": []},
            {"messages": []},
            "abcdefab-abcd-abcd-abcd-abcdefabcdef",
        ),
        (
            {
                "messages": [
                    {
                        "content": "1",
                        "custom_content": {
                            "state": [
                                {State.SESSION_ID_KEY: "session_id_key", "foo": "bar"}
                            ]
                        },
                    },
                ]
            },
            {
                "messages": [
                    {"content": "1", "custom_content": {"state": [{"foo": "bar"}]}}
                ]
            },
            "session_id_key",
        ),
    ],
)
async def on_request(
    interceptor, fixed_uuid, request_income, request_expected, session_id_expected
):
    request_returned = await interceptor.on_request(request=request_income)
    assert request_expected == request_returned
    assert session_id_expected == interceptor.session_id
    assert interceptor.request_deployment_id == "deployment_123"
    assert interceptor.request_model == "gpt-4"


@pytest.mark.asyncio
async def test_on_stream_start(interceptor):
    before_time = datetime.now()
    await interceptor.on_stream_start()
    after_time = datetime.now()
    assert before_time <= interceptor.start_time <= after_time


@pytest.mark.asyncio
@pytest.mark.parametrize("track_user_data", [False, True])
async def test_on_stream_end(interceptor, track_user_data):
    interceptor.start_time = datetime.now()
    interceptor.config.track_user_data = track_user_data
    interceptor.request_deployment_id = "deployment_123"
    interceptor.request_model = "gpt-4"

    with patch(
        "ai_dial_interceptors_langfuse.langfuse_interceptor.LangfuseClient"
    ) as MockLangfuseClient, patch.object(
        LangfuseInterceptor, "_get_user_email", new=MagicMock()
    ) as mock_get_user_email, patch.object(
        LangfuseInterceptor, "_get_model_info", new=MagicMock()
    ) as mock_get_model_info:
        mock_instance = MockLangfuseClient.return_value
        mock_instance.transmit = MagicMock()

        before_time = datetime.now()
        await interceptor.on_stream_end()
        after_time = datetime.now()

        MockLangfuseClient.assert_called_once_with(
            session_id=interceptor.session_id,
            tags=[
                "gpt-4",
                "deployment_123",
            ],
            request_messages=interceptor.request.messages,
            response_message=interceptor.response_message,
            model_name="gpt-4",
            deployment_id="deployment_123",
            start_time=interceptor.start_time,
            end_time=interceptor.end_time,
            user_id=interceptor.user_email,
            langfuse_secret_key=interceptor.config.langfuse.secret_key,
            langfuse_public_key=interceptor.config.langfuse.public_key,
            langfuse_host=interceptor.config.langfuse.host,
            metadata={
                "model": "gpt-4",
                "deployment_id": "deployment_123",
                "x_conversation_id": "",
                "is_model": False,
                "model_info": {},
            },
            is_model=False,
        )

        assert before_time <= interceptor.end_time <= after_time
        mock_instance.transmit.assert_called_once()
        mock_get_model_info.assert_called_once_with(
            interceptor.dial_client.storage.api_key
        )
        if track_user_data:
            mock_get_user_email.assert_called_once_with(
                interceptor.dial_client.storage.api_key
            )
        else:
            mock_get_user_email.assert_not_called()
