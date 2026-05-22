#!/usr/bin/env python3
"""Generate the staged DMG background image for BattMon."""

from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 700
HEIGHT = 463


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/SFNSDisplay-Bold.otf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/SFNS.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _vertical_gradient(height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> list[tuple[int, int, int]]:
    rows = []
    for y_pos in range(height):
        ratio = y_pos / max(height - 1, 1)
        rows.append(
            tuple(
                int(top[channel] + (bottom[channel] - top[channel]) * ratio)
                for channel in range(3)
            )
        )
    return rows


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def main() -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (21, 24, 31, 255))
    draw = ImageDraw.Draw(image)

    for y_pos, color in enumerate(_vertical_gradient(HEIGHT, (31, 34, 42), (16, 18, 24))):
        draw.line([(0, y_pos), (WIDTH, y_pos)], fill=color + (255,), width=1)

    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([92, 76, 292, 246], fill=(52, 211, 153, 56))
    glow_draw.ellipse([404, 86, 614, 256], fill=(96, 165, 250, 44))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    image = Image.alpha_composite(image, glow)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle([28, 28, WIDTH - 28, HEIGHT - 28], radius=24, outline=(255, 255, 255, 18), width=1)
    draw.line([(54, 318), (WIDTH - 54, 318)], fill=(255, 255, 255, 28), width=1)

    brand_font = _load_font(30, bold=True)
    subtitle_font = _load_font(15)
    section_font = _load_font(22, bold=True)
    body_font = _load_font(15)
    body_emphasis_font = _load_font(15, bold=True)
    tertiary_font = _load_font(14)
    icon_label_font = _load_font(18, bold=True)

    draw.text((56, 50), "BattMon", fill=(244, 247, 251, 255), font=brand_font)
    draw.text((56, 92), "Lightweight battery alerts for macOS", fill=(177, 187, 201, 255), font=subtitle_font)

    arrow_center_x = WIDTH // 2
    arrow_center_y = 168

    draw.polygon(
        [
            (arrow_center_x - 58, arrow_center_y - 3),
            (arrow_center_x + 8, arrow_center_y - 3),
            (arrow_center_x + 8, arrow_center_y - 15),
            (arrow_center_x + 46, arrow_center_y),
            (arrow_center_x + 8, arrow_center_y + 15),
            (arrow_center_x + 8, arrow_center_y + 3),
            (arrow_center_x - 58, arrow_center_y + 3),
        ],
        fill=(229, 236, 246, 224),
    )

    battmon_label = "BattMon"
    applications_label = "Applications"
    battmon_x = 180 - (_text_width(draw, battmon_label, icon_label_font) // 2)
    applications_x = 520 - (_text_width(draw, applications_label, icon_label_font) // 2)
    label_y = 226
    draw.text((battmon_x, label_y), battmon_label, fill=(244, 247, 251, 255), font=icon_label_font)
    draw.text((applications_x, label_y), applications_label, fill=(244, 247, 251, 255), font=icon_label_font)

    draw.text((56, 330), "Install BattMon", fill=(244, 247, 251, 255), font=section_font)
    draw.text((56, 360), "Drag BattMon.app into Applications", fill=(229, 236, 246, 255), font=body_emphasis_font)
    draw.text((56, 386), "If blocked:", fill=(177, 187, 201, 255), font=tertiary_font)
    draw.text((56, 408), "Privacy & Security -> Open Anyway", fill=(229, 236, 246, 255), font=body_emphasis_font)

    image.save("assets/dmg_background@2x.png")
    print("DMG background written to assets/dmg_background@2x.png")


if __name__ == "__main__":
    main()
