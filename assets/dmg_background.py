#!/usr/bin/env python3
"""Generate the staged DMG background image for BattMon."""

from PIL import Image, ImageDraw


WIDTH = 520
HEIGHT = 320


def main() -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (28, 28, 30, 255))
    draw = ImageDraw.Draw(image)

    draw.rectangle([0, HEIGHT - 96, WIDTH, HEIGHT], fill=(242, 244, 248, 235))

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

    # Keep label areas aligned with Finder icon captions and above the bottom edge.
    # Keep the background minimal; Finder renders icon labels for app and Applications.

    image.save("assets/dmg_background@2x.png")
    print("DMG background written to assets/dmg_background@2x.png")


if __name__ == "__main__":
    main()
