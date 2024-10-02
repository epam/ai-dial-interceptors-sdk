from aidial_sdk import DIALApp
from aidial_sdk.telemetry.types import TelemetryConfig

from aidial_interceptors_sdk.chat_completion import (
    interceptor_to_chat_completion,
)
from aidial_interceptors_sdk.embeddings.adapter import interceptor_to_embeddings
from aidial_interceptors_sdk.examples.registry import (
    chat_completion_interceptors,
    embeddings_interceptors,
)
from aidial_interceptors_sdk.examples.utils.log_config import configure_loggers
from aidial_interceptors_sdk.utils._env import get_env

app = DIALApp(
    description="Examples of DIAL interceptors",
    telemetry_config=TelemetryConfig(),
    add_healthcheck=True,
    dial_url=get_env("DIAL_URL"),
    propagate_auth_headers=True,
)

configure_loggers()

for id, cls in embeddings_interceptors.items():
    app.add_embeddings(id, interceptor_to_embeddings(cls))

for id, cls in chat_completion_interceptors.items():
    app.add_chat_completion(id, interceptor_to_chat_completion(cls))
