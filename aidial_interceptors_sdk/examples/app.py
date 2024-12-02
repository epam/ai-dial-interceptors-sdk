from aidial_interceptors_sdk.examples.app_factory import create_app
from aidial_interceptors_sdk.examples.registry import EXAMPLE_INTERCEPTORS
from aidial_interceptors_sdk.utils._env import get_env
from aidial_interceptors_sdk.utils._http_client import get_http_client

dial_url = get_env("DIAL_URL")


async def client_factory():
    return get_http_client()


app = create_app(
    dial_url=dial_url,
    client_factory=client_factory,
    interceptors=EXAMPLE_INTERCEPTORS,
)
