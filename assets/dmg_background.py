#!/usr/bin/env python3
"""Generate the staged DMG background image for Battery Alert."""

from PIL import Image, ImageDraw, ImageFont


# Match the Finder window content area used in create_dmg.sh (480x300)
WIDTH = 480
HEIGHT = 300


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def main() -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (28, 28, 30, 255))
    draw = ImageDraw.Draw(image)

    for inset in range(42):
        alpha = int(55 * (inset / 42))
        draw.rectangle([inset, inset, WIDTH - inset, HEIGHT - inset], outline=(0, 0, 0, alpha))

    arrow_center_x = WIDTH // 2
    arrow_center_y = HEIGHT // 2 - 2

    # Compact, readable arrow for drag direction.
    draw.polygon(
        [
            (arrow_center_x - 34, arrow_center_y - 12),
            (arrow_center_x + 8, arrow_center_y - 12),
            (arrow_center_x + 8, arrow_center_y - 24),
            (arrow_center_x + 44, arrow_center_y),
            (arrow_center_x + 8, arrow_center_y + 24),
            (arrow_center_x + 8, arrow_center_y + 12),
            (arrow_center_x - 34, arrow_center_y + 12),
        ],
        fill=(255, 255, 255, 120),
    )

    font = _load_font(18)
    text = "Drag Battery Alert to Applications"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(((WIDTH - text_width) // 2, HEIGHT - 34), text, fill=(255, 255, 255, 165), font=font)

    image.save("assets/dmg_background@2x.png")
    print("DMG background written to assets/dmg_background@2x.png")


if __name__ == "__main__":
    main()