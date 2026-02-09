"""Generate DMG background image for Kiroku Memory installer."""

from PIL import Image, ImageDraw

# DMG window: 660×400, generate @2x (1320×800)
W, H = 1320, 800

img = Image.new("RGB", (W, H))
draw = ImageDraw.Draw(img)

# Light gradient background (top-to-bottom, soft warm white)
for y in range(H):
    r = int(235 + (225 - 235) * y / H)
    g = int(238 + (228 - 238) * y / H)
    b = int(242 + (235 - 242) * y / H)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# Icon positions at @2x: app=(180,170) -> (360,340), folder=(480,170) -> (960,340)
app_cx, app_cy = 360, 340
folder_cx, folder_cy = 960, 340
arrow_y = 340

# Draw arrow from app to folder (leave room for icon ~128px @2x radius)
arrow_left = app_cx + 180
arrow_right = folder_cx - 180
arrow_color = (90, 130, 190)
arrow_color_dim = (140, 170, 210)

# Arrow shaft
shaft_h = 6
for i in range(3):
    alpha_color = (
        arrow_color_dim[0] + (arrow_color[0] - arrow_color_dim[0]) * i // 2,
        arrow_color_dim[1] + (arrow_color[1] - arrow_color_dim[1]) * i // 2,
        arrow_color_dim[2] + (arrow_color[2] - arrow_color_dim[2]) * i // 2,
    )
    draw.rounded_rectangle(
        [arrow_left + i * 20, arrow_y - shaft_h, arrow_right - 30, arrow_y + shaft_h],
        radius=shaft_h,
        fill=alpha_color,
    )

# Arrowhead (triangle pointing right)
head_size = 28
draw.polygon(
    [
        (arrow_right, arrow_y),
        (arrow_right - head_size * 2, arrow_y - head_size),
        (arrow_right - head_size * 2, arrow_y + head_size),
    ],
    fill=arrow_color,
)

# Dashed line effect on shaft (subtle dots)
for x in range(arrow_left + 40, arrow_right - 60, 40):
    draw.ellipse([x - 3, arrow_y - 3, x + 3, arrow_y + 3], fill=(220, 225, 232))

# Save
out = "desktop/src-tauri/images/dmg-background.png"
img.save(out, "PNG", dpi=(144, 144))
print(f"Generated {out} ({W}x{H} @2x)")
