"""
生成 PWA 圖示的腳本
需要安裝 Pillow: pip install Pillow
"""
from PIL import Image, ImageDraw, ImageFont
import os

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def create_icon(size):
    # 創建漸變背景
    img = Image.new('RGB', (size, size))
    draw = ImageDraw.Draw(img)

    # 漸變背景
    for y in range(size):
        ratio = y / size
        r = int(99 + (168 - 99) * ratio)
        g = int(102 + (85 - 102) * ratio)
        b = int(241 + (247 - 241) * ratio)
        for x in range(size):
            draw.point((x, y), fill=(r, g, b))

    # 繪製相機圖示
    center = size // 2
    outer_r = int(size * 0.35)
    inner_r = int(size * 0.15)

    draw.ellipse([center - outer_r, center - outer_r, center + outer_r, center + outer_r],
                 outline='white', width=max(2, size // 20))
    draw.ellipse([center - inner_r, center - inner_r, center + inner_r, center + inner_r],
                 fill='white')

    # 繪製矩形（機身）
    body_width = int(size * 0.5)
    body_height = int(size * 0.3)
    body_top = center + int(outer_r * 0.5)
    draw.rectangle([center - body_width // 2, body_top,
                    center + body_width // 2, body_top + body_height],
                   fill='white')

    # 繪製按鈕
    btn_size = int(size * 0.15)
    btn_x = center + int(body_width * 0.3)
    btn_y = body_top + body_height // 2
    draw.ellipse([btn_x - btn_size // 2, btn_y - btn_size // 2,
                    btn_x + btn_size // 2, btn_y + btn_size // 2],
                 fill=(99, 102, 241))

    return img

if __name__ == '__main__':
    for size in SIZES:
        img = create_icon(size)
        filename = os.path.join(OUTPUT_DIR, f'icon-{size}.png')
        img.save(filename, 'PNG')
        print(f'Created: {filename}')

    print('All icons generated!')
