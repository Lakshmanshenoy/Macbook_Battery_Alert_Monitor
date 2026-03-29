#!/usr/bin/env python3
"""Generate battery icon for macOS app"""

from PIL import Image, ImageDraw
from pathlib import Path

def create_battery_icon(size):
    """Create a battery icon at the specified size"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors
    color_fill = (76, 175, 80, 255)  # Green
    color_border = (56, 142, 60, 255)  # Darker green
    
    # Battery body dimensions (relative to size)
    margin = int(size * 0.1)
    battery_width = size - (2 * margin)
    battery_height = int(size * 0.6)
    battery_top = int((size - battery_height) / 2)
    battery_left = margin
    
    # Battery terminal (nub) at the top right
    terminal_width = int(battery_width * 0.15)
    terminal_height = int(battery_height * 0.3)
    terminal_left = battery_left + battery_width
    terminal_top = battery_top + int((battery_height - terminal_height) / 2)
    
    # Draw battery body with border
    radius = int(size * 0.08)
    draw.rounded_rectangle(
        [(battery_left, battery_top), 
         (battery_left + battery_width - int(terminal_width/2), battery_top + battery_height)],
        fill=color_fill,
        outline=color_border,
        width=max(1, int(size * 0.02))
    )
    
    # Draw battery terminal
    terminal_rect = [
        (terminal_left - int(terminal_width/2), terminal_top),
        (terminal_left, terminal_top + terminal_height)
    ]
    draw.rectangle(terminal_rect, fill=color_fill, outline=color_border, 
                   width=max(1, int(size * 0.02)))
    
    # Draw battery charge indicator (80% full)
    charge_percentage = 0.8
    charge_width = (battery_width - int(terminal_width/2) - 2*margin) * charge_percentage
    charge_height = battery_height - 2*margin
    charge_left = battery_left + margin
    charge_top = battery_top + margin
    
    draw.rectangle(
        [(charge_left, charge_top),
         (charge_left + charge_width, charge_top + charge_height)],
        fill=(76, 175, 80, 255)
    )
    
    return img

# Create icon directory
icon_dir = Path("BatteryAlert.iconset")
icon_dir.mkdir(exist_ok=True)

# Generate all required icon sizes for .icns
sizes = [16, 32, 64, 128, 256, 512, 1024]

for size in sizes:
    img = create_battery_icon(size)
    filename_1x = f"icon_{size}x{size}.png"
    img.save(icon_dir / filename_1x)
    print(f"Created {filename_1x}")
    
    # Create @2x versions for sizes up to 512
    if size < 512:
        filename_2x = f"icon_{size}x{size}@2x.png"
        img_2x = create_battery_icon(size * 2)
        img_2x.save(icon_dir / filename_2x)
        print(f"Created {filename_2x}")

print(f"\n✅ Icon files created in {icon_dir}")
