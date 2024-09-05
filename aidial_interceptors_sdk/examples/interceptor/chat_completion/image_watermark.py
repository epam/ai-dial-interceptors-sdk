import base64

from aidial_sdk.exceptions import InvalidRequestError
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from aidial_interceptors_sdk.examples.utils.watermark.stamp import (
    stamp_watermark,
)


class ImageWatermarkInterceptor(ChatCompletionInterceptor):

    @override
    async def on_response_attachment(self, path, attachment: dict) -> dict:
        ty = attachment.get("type")

        if ty == "image/jpeg":
            format = "JPEG"
        elif ty == "image/png":
            format = "PNG"
        else:
            return attachment

        url = attachment.get("url")
        if url is not None:
            dial_url = self.dial_client.storage.to_dial_url(url)
            if dial_url is None:
                return attachment

            data = await self.dial_client.storage.download(url)
            data = stamp_watermark(data, format)

            # overwrite the original image
            await self.dial_client.storage.upload(url, ty, data)

        data = attachment.get("data")
        if data is not None:
            try:
                bytes = base64.b64decode(data)
            except Exception:
                raise InvalidRequestError(
                    "Attachment data isn't base64 encoded",
                )

            bytes = stamp_watermark(bytes, format)
            attachment = {
                **attachment,
                "data": base64.b64encode(bytes).decode("utf-8"),
            }

        return attachment
