from PIL import Image, ImageDraw, ImageFont
import os

font_path = r'C:\Windows\Fonts\yumin.ttf'
if not os.path.exists(font_path):
    font_path = r'C:\Windows\Fonts\msmincho.ttc'

size = 512
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

corner_radius = 96
bg_color = (28, 25, 23, 255)  # #1C1917
draw.rounded_rectangle([0, 0, size, size], radius=corner_radius, fill=bg_color)

font = ImageFont.truetype(font_path, 320)
bbox = draw.textbbox((0, 0), '漢', font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]
x = (size - text_w) / 2 - bbox[0]
y = (size - text_h) / 2 - bbox[1] - 8

draw.text((x, y), '漢', fill=(255, 255, 255, 255), font=font)

os.makedirs('public', exist_ok=True)

# Generate multi-size ICO
ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
img.save('favicon.ico', format='ICO', sizes=ico_sizes)
img.save('public/favicon.ico', format='ICO', sizes=ico_sizes)

# Generate PNGs
img_32 = img.resize((32, 32), Image.Resampling.LANCZOS)
img_32.save('favicon.png')
img_32.save('public/favicon.png')

img_180 = img.resize((180, 180), Image.Resampling.LANCZOS)
img_180.save('apple-touch-icon.png')
img_180.save('public/apple-touch-icon.png')

# SVG Favicon
svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#1C1917"/>
  <text x="32" y="35" dominant-baseline="central" text-anchor="middle" fill="#FFFFFF" font-family="'Noto Serif JP', 'Yu Mincho', serif" font-weight="700" font-size="40">漢</text>
</svg>"""

with open('favicon.svg', 'w', encoding='utf-8') as f:
    f.write(svg_content)
with open('public/favicon.svg', 'w', encoding='utf-8') as f:
    f.write(svg_content)

if os.path.exists('test_icon.png'):
    os.remove('test_icon.png')

print('All favicon assets generated successfully!')
