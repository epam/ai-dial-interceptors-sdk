import io
from functools import cache
from typing import Literal

from PIL import Image
from PIL.Image import Image as ImageObject

from aidial_interceptors_sdk.examples.utils.watermark.generate import (
    gen_watermark_image,
)


def _resize_tiling(image: ImageObject, box: tuple[int, int]) -> ImageObject:
    width, height = box
    tiled_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    img_width, img_height = image.size

    for x in range(0, width + img_width, img_width):
        for y in range(0, height + img_height, img_height):
            tiled_image.paste(image, (x, y))

    return tiled_image


def _stamp_watermark_image(
    image: ImageObject, watermark: ImageObject
) -> ImageObject:
    tiled_watermark = _resize_tiling(watermark, image.size)

    if image.mode != "RGBA":
        image = image.convert("RGBA")
    if tiled_watermark.mode != "RGBA":
        tiled_watermark = tiled_watermark.convert("RGBA")

    watermarked_image = Image.alpha_composite(image, tiled_watermark)

    return watermarked_image


@cache
def _watermark_image() -> ImageObject:
    return gen_watermark_image("EPAM DIAL")


def stamp_watermark(
    image_bytes: bytes, output_format: Literal["JPEG", "PNG"]
) -> bytes:

    image = Image.open(io.BytesIO(image_bytes))

    watermarked_image = _stamp_watermark_image(image, _watermark_image())

    output_bytes = io.BytesIO()
    watermarked_image.save(output_bytes, format=output_format)

    return output_bytes.getvalue()
