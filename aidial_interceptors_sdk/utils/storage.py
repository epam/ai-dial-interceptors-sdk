import io
import logging
from typing import Mapping
from urllib.parse import urljoin

import httpx
from aidial_sdk.pydantic_v1 import BaseModel

_log = logging.getLogger(__name__)


class FileStorage(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    dial_url: str
    api_key: str
    http_client: httpx.AsyncClient

    @property
    def headers(self) -> Mapping[str, str]:
        return {"api-key": self.api_key}

    async def upload(
        self, url: str, content_type: str | None, content: bytes
    ) -> None:
        if self.to_dial_url(url) is None:
            raise ValueError(f"URL isn't DIAL url: {url!r}")
        url = self._to_abs_url(url)

        response = await self.http_client.put(
            url=url,
            files={"file": (url, io.BytesIO(content), content_type)},
            headers=self.headers,
        )
        response.raise_for_status()

        meta = response.json()

        _log.debug(f"uploaded file: url={url!r}, metadata={meta}")

    def to_dial_url(self, link: str) -> str | None:
        url = self._to_abs_url(link)
        base_url = f"{self.dial_url}/v1/"
        if url.startswith(base_url):
            return url.removeprefix(base_url)
        return None

    def _to_abs_url(self, link: str) -> str:
        base_url = f"{self.dial_url}/v1/"
        return urljoin(base_url, link)

    async def download(self, url: str) -> bytes:
        if self.to_dial_url(url) is None:
            raise ValueError(f"URL isn't DIAL url: {url!r}")
        url = self._to_abs_url(url)

        response = await self.http_client.get(url, headers=self.headers)
        response.raise_for_status()
        return response.content
