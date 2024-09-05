import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as ImageObject


def _find_seamless_crop(image: ImageObject) -> tuple[int, int, int, int]:
    width, height = image.size

    image_gray = image.convert("L")
    pixels = np.array(image_gray)

    min_diff = np.inf
    min_x = -1
    x_diffs = []

    for x in range(10, width):
        diff = np.abs(pixels[:, 0] - pixels[:, x]).sum()
        x_diffs.append(int(diff))
        if diff < min_diff:
            min_diff = diff
            min_x = x

    vertical_seam = min_x

    min_diff = np.inf
    min_y = -1
    y_diffs = []

    for y in range(10, height):
        diff = np.abs(pixels[0, :] - pixels[y, :]).sum()
        y_diffs.append(int(diff))
        if diff < min_diff:
            min_diff = diff
            min_y = y

    horizontal_seam = min_y

    return (0, 0, vertical_seam, horizontal_seam)


def _create_watermark_texture(
    *,
    text: str,
    size: int = 800,
    font_size: int = 60,
    angle: int = 45,
) -> ImageObject:

    padded_size = int(size * math.sqrt(2))
    image_size = (padded_size, padded_size)
    background_color = (255, 255, 255, 0)
    image = Image.new("RGBA", image_size, background_color)

    draw = ImageDraw.Draw(image)

    font_size = 60
    font = ImageFont.load_default(font_size)

    text = "EPAM DIAL"
    text_color = (0, 0, 0, 128)  # Semi-transparent black

    text_width = int(draw.textlength(text, font=font))
    text_height = font_size

    text_layer = Image.new("RGBA", image_size, (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_layer)

    for i in range(-50, 50):
        for j in range(-50, 50):
            text_position = (
                i * (text_width + 5),
                j * (text_height + 0),
            )

            text_draw.text(text_position, text, font=font, fill=text_color)

    text_layer = text_layer.rotate(angle, expand=0)

    image.paste(text_layer, (0, 0), text_layer)

    margin = (padded_size - size) // 2
    return image.crop(
        (margin, margin, padded_size - margin, padded_size - margin)
    )


def gen_watermark_image(text: str) -> ImageObject:
    image = _create_watermark_texture(text=text)
    crop_box = _find_seamless_crop(image)
    return image.crop(crop_box)


if __name__ == "__main__":
    gen_watermark_image("EPAM DIAL").save("watermark.png", "PNG")
