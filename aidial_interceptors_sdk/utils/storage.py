import io
import logging
import mimetypes
from typing import Mapping, Optional, TypedDict
from urllib.parse import urljoin

import aiohttp
from aidial_sdk.pydantic_v1 import BaseModel

_log = logging.getLogger(__name__)


class FileMetadata(TypedDict):
    name: str
    parentPath: str
    bucket: str
    url: str


class Bucket(TypedDict):
    bucket: str
    appdata: str | None  # Users do not have appdata


class AccessDeniedError(Exception):
    def __init__(self, url: str):
        super().__init__(f"Access denied: {url!r}")
        self.url = url


class FileStorage(BaseModel):
    dial_url: str
    api_key: str

    bucket: Optional[Bucket] = None

    @property
    def headers(self) -> Mapping[str, str]:
        return {"api-key": self.api_key}

    async def get_bucket(self, session: aiohttp.ClientSession) -> Bucket:
        if self.bucket is not None:
            return self.bucket

        _log.debug(f"retrieving bucket for {self.dial_url!r}")

        async with session.get(
            f"{self.dial_url}/v1/bucket",
            headers=self.headers,
        ) as response:
            response.raise_for_status()
            bucket = await response.json()
            self.bucket = bucket
            _log.debug(f"bucket: {self.bucket}")
            return bucket

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

    async def is_accessible(
        self, url: str, session: aiohttp.ClientSession
    ) -> bool:
        try:
            await self._get_metadata(url, session)
            _log.debug(f"file is accessible: url={url!r}")
            return True
        except AccessDeniedError:
            _log.debug(f"file isn't accessible: url={url!r}")
            return False

    def to_metadata_url(self, url: str) -> str:
        """
        The file metadata URL given url like: files/BUCKET/foo/baz/document.pdf
        """
        metadata_url = f"{self.dial_url}/v1/metadata/"
        return urljoin(metadata_url, url, allow_fragments=True)

    async def _get_metadata(
        self,
        url: str,
        session: aiohttp.ClientSession,
    ) -> dict:
        metadata_url = self.to_metadata_url(url)

        _log.debug(f"retrieving metadata: file={url!r}, url={metadata_url!r}")

        async with session.get(metadata_url, headers=self.headers) as response:
            if not response.ok:
                match response.status:
                    case 403:
                        raise AccessDeniedError(url)
                    case _:
                        response.raise_for_status()

            metadata = await response.json()

            _log.debug(
                f"retrieved metadata: file={url!r}, url={metadata_url!r}, metadata={metadata}"
            )

            return metadata

    async def upload_file(
        self,
        filename: str,
        content_type: str | None,
        content: bytes,
        session: aiohttp.ClientSession,
    ) -> FileMetadata:
        bucket = await self.get_bucket(session)
        appdata = bucket["appdata"]
        ext = (content_type and mimetypes.guess_extension(content_type)) or ""
        url = f"{self.dial_url}/v1/files/{appdata}/{filename}{ext}"
        return await self.upload(url, content_type, content)

    async def upload(
        self, url: str, content_type: str | None, content: bytes
    ) -> FileMetadata:
        if self.to_dial_url(url) is None:
            raise ValueError(f"URL isn't DIAL url: {url!r}")
        url = self.to_abs_url(url)

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
                return meta

    def to_dial_url(self, link: str) -> str | None:
        url = self.to_abs_url(link)
        base_url = f"{self.dial_url}/v1/"
        if url.startswith(base_url):
            return url.removeprefix(base_url)
        return None

    def to_abs_url(self, link: str) -> str:
        base_url = f"{self.dial_url}/v1/"
        ret = urljoin(base_url, link)
        return ret

    async def download(self, url: str) -> bytes:
        if self.to_dial_url(url) is None:
            raise ValueError(f"URL isn't DIAL url: {url!r}")
        url = self.to_abs_url(url)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.read()
