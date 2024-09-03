import io
from functools import cache
from typing import Literal

from PIL import Image
from PIL.Image import Image as ImageObject

from examples.utils.path import package_root_dir


def resize_tiling(image: ImageObject, box: tuple[int, int]) -> ImageObject:
    width, height = box
    tiled_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    img_width, img_height = image.size

    for x in range(0, width + img_width, img_width):
        for y in range(0, height + img_height, img_height):
            tiled_image.paste(image, (x, y))

    return tiled_image


def stamp_watermark_image(
    image: ImageObject, watermark: ImageObject
) -> ImageObject:
    tiled_watermark = resize_tiling(watermark, image.size)

    if image.mode != "RGBA":
        image = image.convert("RGBA")
    if tiled_watermark.mode != "RGBA":
        tiled_watermark = tiled_watermark.convert("RGBA")

    watermarked_image = Image.alpha_composite(image, tiled_watermark)

    return watermarked_image


@cache
def watermark_image() -> ImageObject:
    return Image.open(package_root_dir() / "assets" / "watermark.png")


def stamp_watermark(
    image_bytes: bytes, output_format: Literal["JPEG", "PNG"]
) -> bytes:

    image = Image.open(io.BytesIO(image_bytes))

    watermarked_image = stamp_watermark_image(image, watermark_image())

    output_bytes = io.BytesIO()
    watermarked_image.save(output_bytes, format=output_format)

    return output_bytes.getvalue()
