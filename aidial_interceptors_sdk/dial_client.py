from aidial_sdk.exceptions import InvalidRequestError
from aidial_sdk.pydantic_v1 import BaseModel
from openai import AsyncAzureOpenAI

from aidial_interceptors_sdk.utils._env import get_env
from aidial_interceptors_sdk.utils._http_client import get_http_client
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
            raise InvalidRequestError("The 'api-key' request header is missing")

        client = AsyncAzureOpenAI(
            azure_endpoint=DIAL_URL,
            azure_deployment="interceptor",
            api_key=api_key,
            # NOTE: api-version query parameter is not required in the chat completions DIAL API.
            # However, it is required in Azure OpenAI API, that's why the openai library fails when it's missing:
            # https://github.com/openai/openai-python/blob/9850c169c4126fd04dc6796e4685f1b9e4924aa4/src/openai/lib/azure.py#L174-L177
            #
            # A workaround for it could be to patch the AsyncAzureOpenAI class in order to disable the check.
            # This would be hard to maintain though.
            #
            # However, since DIAL OpenAI adapter treats a missing api-version in the same way as an empty string,
            # we could actually default the api-version to an empty string here too.
            # DIAL OpenAI adapter is the only place where api-version has any effect,
            # so the query param modification is safe.
            # https://github.com/epam/ai-dial-adapter-openai/blob/b462d1c26ce8f9d569b9c085a849206aad91becf/aidial_adapter_openai/app.py#L93
            api_version=api_version or "",
            max_retries=0,
            http_client=get_http_client(),
        )

        storage = FileStorage(dial_url=DIAL_URL, api_key=api_key)

        return cls(client=client, storage=storage)
