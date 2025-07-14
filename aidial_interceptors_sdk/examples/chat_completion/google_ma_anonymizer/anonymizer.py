from __future__ import annotations

import asyncio
import base64
import logging
import mimetypes
from functools import cached_property
from typing import Any, List, Optional

from google.api_core.exceptions import GoogleAPICallError
from google.auth import default as adc_default
from google.cloud import dlp_v2
from google.oauth2 import service_account

_LOG = logging.getLogger("gcp.guard")


class GuardError(RuntimeError):
    """Wraps any DLP-level errors so callers don’t depend on google-api-core."""


class GCPModelArmorPromptsGuard:
    """
    Async wrapper around Google Cloud DLP without a custom ThreadPoolExecutor.
    Blocking RPCs are dispatched to the loop’s default executor.
    """

    def __init__(
        self,
        *,
        project: str,
        region: str,
        inspect_template: str,
        deidentify_template: str,
        surrogate_info_type: str,
        kms_key_name: str,
        wrapped_key: str,
        key_file: str | None = None,
    ) -> None:
        self.project = project
        self.region = region
        self.inspect_template_id = inspect_template
        self.deidentify_template_id = deidentify_template
        self.surrogate_info_type = surrogate_info_type
        self.kms_key_name = kms_key_name
        self.wrapped_key = wrapped_key
        self._key_file = key_file
        self.parent = f"projects/{project}/locations/{region}"
        self.inspect_template_name = (
            f"{self.parent}/inspectTemplates/{inspect_template}"
        )
        self.deidentify_template_name = (
            f"{self.parent}/deidentifyTemplates/{deidentify_template}"
        )

    @cached_property
    def _client(self) -> dlp_v2.DlpServiceClient:
        if self._key_file:
            creds = service_account.Credentials.from_service_account_file(
                self._key_file
            )
        else:
            creds, _ = adc_default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )

        return dlp_v2.DlpServiceClient(credentials=creds)

    async def _io(self, func, /, **kw) -> Any:
        try:
            return await asyncio.to_thread(func, **kw)
        except GoogleAPICallError as exc:
            _LOG.error("DLP call failed: %s", exc)
            raise GuardError(str(exc)) from exc

    async def deidentify(self, text: str) -> str:
        if not text.strip():  # handles None, "", and whitespace-only
            return ""
        req = {
            "parent": self.parent,
            "inspect_template_name": self.inspect_template_name,
            "deidentify_template_name": self.deidentify_template_name,
            "item": {"value": text},
        }
        resp = await self._io(self._client.deidentify_content, request=req)
        return resp.item.value

    async def reidentify(self, text: str) -> str:
        if not text.strip():  # handles None, "", and whitespace-only
            return ""
        crypto_cfg = dlp_v2.CryptoDeterministicConfig(
            crypto_key=dlp_v2.CryptoKey(
                kms_wrapped=dlp_v2.KmsWrappedCryptoKey(
                    crypto_key_name=self.kms_key_name,
                    wrapped_key=self.wrapped_key,
                )
            ),
            surrogate_info_type=dlp_v2.InfoType(name=self.surrogate_info_type),
        )
        reid_cfg = dlp_v2.DeidentifyConfig(
            info_type_transformations=dlp_v2.InfoTypeTransformations(
                transformations=[
                    dlp_v2.InfoTypeTransformations.InfoTypeTransformation(
                        info_types=[
                            dlp_v2.InfoType(name=self.surrogate_info_type)
                        ],
                        primitive_transformation=dlp_v2.PrimitiveTransformation(
                            crypto_deterministic_config=crypto_cfg
                        ),
                    )
                ]
            )
        )
        inspect_cfg = dlp_v2.InspectConfig(
            custom_info_types=[
                dlp_v2.CustomInfoType(
                    info_type=dlp_v2.InfoType(name=self.surrogate_info_type),
                    surrogate_type=dlp_v2.CustomInfoType.SurrogateType(),
                )
            ]
        )
        req = {
            "parent": self.parent,
            "inspect_config": inspect_cfg,
            "reidentify_config": reid_cfg,
            "item": {"value": text},
        }
        resp = await self._io(self._client.reidentify_content, request=req)
        return resp.item.value

    async def get_sensitive_fields(self, text: str) -> List[dict]:
        if not text.strip():  # handles None, "", and whitespace-only
            return []
        req = {
            "parent": self.parent,
            "item": {"value": text},
            "inspect_template_name": self.inspect_template_name,
            "inspect_config": {"include_quote": True},
        }
        resp = await self._io(self._client.inspect_content, request=req)
        return [
            {"text": f.quote or "", "infoType": f.info_type.name}
            for f in (resp.result.findings or ())
        ]

    async def deidentify_image(self, file_name: str, data: bytes) -> List[dict]:
        infotypes: list = list(
            self._client.get_inspect_template(
                name=self.inspect_template_name
            ).inspect_config.info_types
        )
        info_types = [{"name": info_type.name} for info_type in infotypes]
        image_redaction_configs = []
        if info_types is not None:
            for info_type in info_types:
                image_redaction_configs.append({"info_type": info_type})
        # Construct the configuration dictionary. Keys which are None may
        # optionally be omitted entirely.
        inspect_config = {
            "min_likelihood": "LIKELY",
            "info_types": info_types,
            "include_quote": True,
        }
        # If mime_type is not specified, guess it from the filename.
        # if mime_type is None:
        mime_guess = mimetypes.MimeTypes().guess_type(file_name)
        mime_type = mime_guess[0] or "application/octet-stream"
        supported_content_types = {
            None: 0,  # "Unspecified" or BYTES_TYPE_UNSPECIFIED
            "image/jpeg": 1,  # IMAGE_JPEG
            "image/bmp": 2,  # IMAGE_BMP
            "image/png": 3,  # IMAGE_PNG
            "image/svg": 4,  # IMAGE_SVG - Adjusted to "image/svg+xml" for correct MIME type
            # Note: No specific MIME type for general "image", mapping to IMAGE for any image type not specified
            "image": 6,  # IMAGE - Any image type
        }
        content_type_index = supported_content_types.get(mime_type, 0)
        if mime_type not in supported_content_types:
            raise ValueError(
                f"Unsupported image MIME type: {mime_type!r}. "
                f"Supported types: {', '.join(k for k in supported_content_types if k)}"
            )
        byte_item = dlp_v2.ByteContentItem(
            type_=content_type_index,
            data=data,
        )
        tmp_parent = f"projects/{self.project}/locations/global"
        response = self._client.redact_image(
            request={
                "parent": tmp_parent,
                "inspect_config": inspect_config,
                "image_redaction_configs": image_redaction_configs,
                "include_findings": True,
                "byte_item": byte_item,
            }
        )
        b64 = base64.b64encode(response.redacted_image).decode()

        findings = [
            {"text": f.quote, "infoType": f.info_type.name}
            for f in response.inspect_result.findings
        ]
        findings.append({"data": b64})
        return findings

    async def close(self) -> None:
        transport = getattr(self._client, "transport", None)
        if transport and hasattr(transport, "close"):
            transport.close()

    # async‐context support
    async def __aenter__(self) -> "GCPModelArmorPromptsGuard":

        return self

    async def __aexit__(self, exc_type, exc, tb) -> Optional[bool]:
        await self.close()

        return None
