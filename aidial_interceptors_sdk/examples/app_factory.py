from aidial_sdk import DIALApp
from aidial_sdk.telemetry.types import TelemetryConfig

from aidial_interceptors_sdk.chat_completion import (
    interceptor_to_chat_completion,
)
from aidial_interceptors_sdk.embeddings.adapter import interceptor_to_embeddings
from aidial_interceptors_sdk.examples.registry import Interceptors
from aidial_interceptors_sdk.examples.utils.log_config import configure_loggers
from aidial_interceptors_sdk.utils._http_client import HTTPClientFactory


def create_app(
    *,
    dial_url: str,
    client_factory: HTTPClientFactory,
    interceptors: Interceptors,
) -> DIALApp:
    app = DIALApp(
        description="Examples of DIAL interceptors",
        dial_url=dial_url,
        telemetry_config=TelemetryConfig(),
        add_healthcheck=True,
        propagate_auth_headers=True,
    )

    configure_loggers()

    for id, cls in interceptors.embeddings.items():
        app.add_embeddings(
            id, interceptor_to_embeddings(cls, dial_url, client_factory)
        )

    for id, cls in interceptors.chat_completions.items():
        app.add_chat_completion(
            id, interceptor_to_chat_completion(cls, dial_url, client_factory)
        )

    return app
