#!/usr/bin/env python3
"""Generate a GitHub social preview image for Battery Alert Monitor.

Supports interactive prompt and CLI args: `python3 generate_social_preview.py 1280 640`
If run without args, the script will ask for a size (e.g. 1280x640) and create
`social_preview_<WxH>.png` in the repo root. Minimum supported size is 640x320.
Also supports `--presets` CLI flag or interactive `presets` keyword to generate common sizes.
"""
from PIL import Image, ImageDraw, ImageFont
import sys

# Default size (can be overridden by user input)
DEFAULT_WIDTH, DEFAULT_HEIGHT = 1280, 640


def parse_size_input(s: str):
    s = s.strip()
    if not s:
        return DEFAULT_WIDTH, DEFAULT_HEIGHT
    # allow formats like '1280x640' or '1280 640'
    if 'x' in s:
        parts = s.split('x')
    else:
        parts = s.split()
    try:
        w = int(parts[0])
        h = int(parts[1])
        return w, h
    except Exception:
        return None


def generate_image(width: int, height: int, outfile: str):
    WIDTH, HEIGHT = width, height

    # Colors
    BG_TOP = (10, 25, 47)
    BG_BOTTOM = (6, 80, 40)
    ACCENT = (76, 175, 80)
    WHITE = (255, 255, 255)

    def draw_gradient(draw):
        for y in range(HEIGHT):
            t = y / (HEIGHT - 1)
            r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
            g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
            b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    def draw_battery(draw, x, y, w, h, charge=0.8):
        # Body
        radius = int(min(w, h) * 0.08)
        body_w = int(w * 0.9)
        body_h = int(h)
        body_x = x
        body_y = y
        # outer rectangle
        draw.rounded_rectangle([body_x, body_y, body_x + body_w, body_y + body_h], radius=radius, fill=(30,30,30,200), outline=ACCENT, width=max(2, int(min(WIDTH, HEIGHT)*0.005)))
        # terminal
        term_w = int(w * 0.06)
        term_h = int(h * 0.4)
        term_x = body_x + body_w + max(2, int(WIDTH*0.002))
        term_y = body_y + (body_h - term_h)//2
        draw.rectangle([term_x, term_y, term_x + term_w, term_y + term_h], fill=ACCENT)
        # charge interior
        padding = max(8, int(min(WIDTH, HEIGHT) * 0.02))
        inner_x = body_x + padding
        inner_y = body_y + padding
        inner_h = body_h - 2*padding
        inner_w = body_w - 2*padding
        charge_w = int(inner_w * charge)
        # background of inner
        draw.rectangle([inner_x, inner_y, inner_x + inner_w, inner_y + inner_h], fill=(50,50,50))
        # filled charge
        draw.rectangle([inner_x, inner_y, inner_x + charge_w, inner_y + inner_h], fill=ACCENT)

    img = Image.new('RGB', (WIDTH, HEIGHT), BG_TOP)
    draw = ImageDraw.Draw(img)

    # background gradient
    draw_gradient(draw)

    # left area: battery large (scale with image)
    battery_w = int(WIDTH * 0.33)
    battery_h = int(HEIGHT * 0.375)
    battery_x = int(WIDTH * 0.09)
    battery_y = (HEIGHT - battery_h) // 2
    draw_battery(draw, battery_x, battery_y, battery_w, battery_h, charge=0.78)

    # Right text - font sizes scale with image height
    title_font_size = max(24, int(HEIGHT * 0.1125))
    sub_font_size = max(14, int(HEIGHT * 0.05625))
    try:
        font_title = ImageFont.truetype('/Library/Fonts/Arial Bold.ttf', title_font_size)
        font_sub = ImageFont.truetype('/Library/Fonts/Arial.ttf', sub_font_size)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    title = "Battery Alert Monitor"
    subtitle = "Lightweight macOS app — real-time battery monitoring & alerts"

    text_x = battery_x + battery_w + int(WIDTH * 0.046)
    text_y = battery_y + int(HEIGHT * 0.03)

    # draw title with subtle shadow
    shadow_offset = max(1, int(HEIGHT * 0.003))

    # Ensure title fits: reduce font size until it fits the available width
    right_margin = int(WIDTH * 0.09)
    max_title_w = WIDTH - text_x - right_margin
    try:
        # If TrueType fonts are available, dynamically adjust size
        base_font_path = '/Library/Fonts/Arial Bold.ttf'
        fs = title_font_size
        fitted = False
        while fs >= 12:
            try:
                trial_font = ImageFont.truetype(base_font_path, fs)
            except Exception:
                break
            tb = draw.textbbox((0, 0), title, font=trial_font)
            tw = tb[2] - tb[0]
            if tw <= max_title_w:
                font_title = trial_font
                fitted = True
                break
            fs -= 2
        if not fitted:
            # fallback: use whatever font_title is (may be smaller default)
            pass
    except Exception:
        pass

    draw.text((text_x + shadow_offset, text_y + shadow_offset), title, font=font_title, fill=(0,0,0,180))
    draw.text((text_x, text_y), title, font=font_title, fill=WHITE)

    # subtitle wrapped
    max_w = WIDTH - text_x - int(WIDTH * 0.094)
    words = subtitle.split()
    lines = []
    cur = ""
    for w in words:
        test = cur + (" " if cur else "") + w
        bbox = draw.textbbox((0, 0), test, font=font_sub)
        tw = bbox[2] - bbox[0]
        if tw <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    line_y = text_y + int(HEIGHT * 0.15625)
    line_spacing = max(20, int(HEIGHT * 0.072))
    for line in lines:
        draw.text((text_x, line_y), line, font=font_sub, fill=(230,230,230))
        line_y += line_spacing

    # small footer
    footer = "Built with Python • PyInstaller • RUMPS"
    ffont = font_sub
    fbbox = draw.textbbox((0, 0), footer, font=ffont)
    fw = fbbox[2] - fbbox[0]
    fh = fbbox[3] - fbbox[1]
    draw.text((WIDTH - fw - int(WIDTH * 0.031), HEIGHT - fh - int(HEIGHT * 0.0375)), footer, font=ffont, fill=(200,200,200))

    img.save(outfile, "PNG")
    print(f"Saved {outfile}")


def main_interactive():
    prompt = f"Enter size WIDTHxHEIGHT (min 640x320). Press Enter for default {DEFAULT_WIDTH}x{DEFAULT_HEIGHT}: "
    while True:
        try:
            user = input(prompt)
        except EOFError:
            user = ""
        # Allow special keyword to generate preset sizes
        if user.strip().lower() in ("presets", "all"):
            presets = [(1280, 640), (640, 320), (1200, 630)]
            for (pw, ph) in presets:
                outfile = f"social_preview_{pw}x{ph}.png"
                generate_image(pw, ph, outfile)
            break

        parsed = parse_size_input(user)
        if parsed is None:
            print("Invalid input. Example formats: 1280x640 or '640 320'. Or type 'presets' to create common sizes.")
            continue
        w, h = parsed
        if w < 640 or h < 320:
            print("Size too small — minimum is 640x320.")
            continue
        outfile = f"social_preview_{w}x{h}.png"
        generate_image(w, h, outfile)
        break


if __name__ == '__main__':
    # Allow non-interactive invocation with CLI args: WIDTH HEIGHT
    if len(sys.argv) == 2 and sys.argv[1] == '--presets':
        presets = [(1280, 640), (640, 320), (1200, 630)]
        for (pw, ph) in presets:
            outfile = f"social_preview_{pw}x{ph}.png"
            generate_image(pw, ph, outfile)
        sys.exit(0)

    if len(sys.argv) == 3:
        try:
            w = int(sys.argv[1])
            h = int(sys.argv[2])
            if w < 640 or h < 320:
                print("Minimum supported size is 640x320")
                sys.exit(1)
            outfile = f"social_preview_{w}x{h}.png"
            generate_image(w, h, outfile)
        except Exception as e:
            print("Invalid arguments:", e)
            sys.exit(1)
    else:
        main_interactive()
