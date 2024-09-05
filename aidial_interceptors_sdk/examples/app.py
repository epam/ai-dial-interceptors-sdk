from aidial_sdk import DIALApp
from aidial_sdk.telemetry.types import TelemetryConfig

from aidial_interceptors_sdk.chat_completion import (
    interceptor_to_chat_completion,
)
from aidial_interceptors_sdk.embeddings import interceptor_to_embeddings_handler
from aidial_interceptors_sdk.examples.registry import (
    chat_completion_interceptors,
    embeddings_interceptors,
)
from aidial_interceptors_sdk.examples.utils.log_config import configure_loggers

app = DIALApp(
    description="Examples of DIAL interceptors",
    telemetry_config=TelemetryConfig(),
    add_healthcheck=True,
)

configure_loggers()

for id, cls in embeddings_interceptors.items():
    app.post(f"/openai/deployments/{id}/embeddings")(
        interceptor_to_embeddings_handler(cls)
    )

for id, cls in chat_completion_interceptors.items():
    app.add_chat_completion(id, interceptor_to_chat_completion(cls))
