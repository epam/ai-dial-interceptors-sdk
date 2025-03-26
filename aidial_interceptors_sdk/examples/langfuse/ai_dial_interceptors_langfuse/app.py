from aidial_interceptors_sdk.utils._env import get_env
from aidial_interceptors_sdk.utils._http_client import get_http_client
from aidial_interceptors_sdk.chat_completion import (
    interceptor_to_chat_completion,
)
from aidial_sdk import DIALApp
from aidial_sdk.telemetry.types import TelemetryConfig
from .langfuse_interceptor import LangfuseInterceptor


async def client_factory():
    return get_http_client()


dial_url = get_env("DIAL_URL")

app = DIALApp(
    description="Examples of DIAL interceptors",
    dial_url=dial_url,
    telemetry_config=TelemetryConfig(),
    add_healthcheck=True,
    propagate_auth_headers=True,
)

app.add_chat_completion(
    "langfuse",
    interceptor_to_chat_completion(LangfuseInterceptor, dial_url, client_factory),
)
