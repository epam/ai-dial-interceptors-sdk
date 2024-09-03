from aidial_sdk.exceptions import invalid_request_error
from aidial_sdk.pydantic_v1 import BaseModel
from openai import AsyncAzureOpenAI

from aidial_interceptors_sdk.utils.env import get_env
from aidial_interceptors_sdk.utils.http_client import get_http_client
from aidial_interceptors_sdk.utils.storage import FileStorage

DIAL_URL = get_env("DIAL_URL")


class DialClient(BaseModel):
    client: AsyncAzureOpenAI
    storage: FileStorage

    class Config:
        arbitrary_types_allowed = True

    @property
    def dial_url(self) -> str:
        return self.storage.dial_url

    @classmethod
    async def create(
        cls, api_key: str | None, api_version: str | None
    ) -> "DialClient":
        if not api_key:
            raise invalid_request_error(
                "The 'api-key' request header is missing"
            )

        client = AsyncAzureOpenAI(
            azure_endpoint=DIAL_URL,
            azure_deployment="interceptor",
            api_key=api_key,
            # NOTE: defaulting missing api-version to an empty string, because
            # 1. openai library doesn't allow for a missing api-version parameter.
            # A workaround for it would be a recreation of AsyncAzureOpenAI with the check disabled:
            # https://github.com/openai/openai-python/blob/9850c169c4126fd04dc6796e4685f1b9e4924aa4/src/openai/lib/azure.py#L174-L177
            # which is really not worth it.
            # 2. OpenAI adapter treats a missing api-version in the same way as an empty string and
            # that's the only place where api-version has any meaning, so the query param modification is safe.
            # https://github.com/epam/ai-dial-adapter-openai/blob/b462d1c26ce8f9d569b9c085a849206aad91becf/aidial_adapter_openai/app.py#L93
            api_version=api_version or "",
            max_retries=0,
            http_client=get_http_client(),
        )

        storage = FileStorage(dial_url=DIAL_URL, api_key=api_key)

        return cls(client=client, storage=storage)
