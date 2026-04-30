from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs('assets', exist_ok=True)

# Create a simple radio wave icon
sizes = [16, 32, 48, 64, 128, 256]
images = []

for size in sizes:
    img  = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark background circle
    margin = size // 8
    draw.ellipse(
        [margin, margin, size-margin, size-margin],
        fill=(30, 60, 30, 255)
    )

    # Radio waves - three arcs
    cx = size // 2
    cy = size // 2
    for i, radius in enumerate([size//6, size//4, size//3]):
        width = max(1, size // 32)
        draw.arc(
            [cx-radius, cy-radius, cx+radius, cy+radius],
            start=200, end=340,
            fill=(0, 255, 100, 255),
            width=width
        )

    # Center dot
    dot = max(2, size // 12)
    draw.ellipse(
        [cx-dot, cy-dot, cx+dot, cy+dot],
        fill=(0, 255, 100, 255)
    )

    images.append(img)

# Save as ICO
images[0].save(
    'assets/icon.ico',
    format='ICO',
    sizes=[(s, s) for s in sizes],
    append_images=images[1:]
)
print("Icon created: assets/icon.ico")