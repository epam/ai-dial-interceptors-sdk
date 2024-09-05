import io
import logging
from typing import Mapping
from urllib.parse import urljoin

import aiohttp
from aidial_sdk.pydantic_v1 import BaseModel

_log = logging.getLogger(__name__)


class FileStorage(BaseModel):
    dial_url: str
    api_key: str

    @property
    def headers(self) -> Mapping[str, str]:
        return {"api-key": self.api_key}

    @staticmethod
    def _to_form_data(
        filename: str, content_type: str | None, content: bytes
    ) -> aiohttp.FormData:
        data = aiohttp.FormData()
        data.add_field(
            "file",
            io.BytesIO(content),
            filename=filename,
            content_type=content_type,
        )
        return data

    async def upload(
        self, url: str, content_type: str | None, content: bytes
    ) -> None:
        if self.to_dial_url(url) is None:
            raise ValueError(f"URL isn't DIAL url: {url!r}")
        url = self._to_abs_url(url)

        data = FileStorage._to_form_data(url, content_type, content)
        async with aiohttp.ClientSession() as session:
            async with session.put(
                url=url,
                data=data,
                headers=self.headers,
            ) as response:
                response.raise_for_status()
                meta = await response.json()
                _log.debug(f"uploaded file: url={url!r}, metadata={meta}")

    def to_dial_url(self, link: str) -> str | None:
        url = self._to_abs_url(link)
        base_url = f"{self.dial_url}/v1/"
        if url.startswith(base_url):
            return url.removeprefix(base_url)
        return None

    def _to_abs_url(self, link: str) -> str:
        base_url = f"{self.dial_url}/v1/"
        ret = urljoin(base_url, link)
        return ret

    async def download(self, url: str) -> bytes:
        if self.to_dial_url(url) is None:
            raise ValueError(f"URL isn't DIAL url: {url!r}")
        url = self._to_abs_url(url)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.read()
