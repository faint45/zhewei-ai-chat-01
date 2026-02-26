# -*- coding: utf-8 -*-
"""生成 PWA 圖標 - 使用 Pillow 繪製簡潔的築未科技 Logo"""
from PIL import Image, ImageDraw, ImageFont
import os

ICONS_DIR = os.path.join("portal", "static", "icons")
SCREENSHOTS_DIR = os.path.join("portal", "static", "screenshots")
os.makedirs(ICONS_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def create_icon(size):
    """生成漸層背景 + ZW 文字的圖標"""
    img = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(img)
    
    # 漸層背景 (#667eea -> #764ba2)
    for y in range(size):
        ratio = y / size
        r = int(102 + (118 - 102) * ratio)
        g = int(126 + (75 - 126) * ratio)
        b = int(234 + (162 - 234) * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    
    # 圓角遮罩
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = size // 5
    mask_draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    img.putalpha(mask)
    
    # 文字 "ZW"
    font_size = size // 3
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    text = "ZW"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2
    y = (size - th) // 2 - bbox[1]
    
    # 白色文字帶陰影
    draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 80), font=font)
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    return img

def create_service_icon(name, color_rgb, size=96):
    """生成服務圖標"""
    img = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(img)
    
    # 純色背景
    for y in range(size):
        draw.line([(0, y), (size, y)], fill=(*color_rgb, 255))
    
    # 圓角
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = size // 5
    mask_draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    img.putalpha(mask)
    
    # 首字母
    font_size = size // 2
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    letter = name[0].upper()
    bbox = draw.textbbox((0, 0), letter, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2
    y = (size - th) // 2 - bbox[1]
    draw.text((x, y), letter, fill=(255, 255, 255, 255), font=font)
    
    return img

def create_screenshot(width, height, label):
    """生成簡單的截圖佔位圖"""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    
    # 漸層背景
    for y in range(height):
        ratio = y / height
        r = int(102 + (118 - 102) * ratio)
        g = int(126 + (75 - 126) * ratio)
        b = int(234 + (162 - 234) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # 標題文字
    font_size = min(width, height) // 10
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    text = "Zhe-Wei Tech"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (width - tw) // 2
    y = height // 3
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    
    sub = label
    try:
        subfont = ImageFont.truetype("arial.ttf", font_size // 2)
    except:
        subfont = font
    bbox2 = draw.textbbox((0, 0), sub, font=subfont)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((width - tw2) // 2, y + font_size + 20), sub, fill=(255, 255, 255, 200), font=subfont)
    
    return img

print("Generating PWA icons...")

# 主圖標
for size in SIZES:
    icon = create_icon(size)
    path = os.path.join(ICONS_DIR, f"icon-{size}x{size}.png")
    icon.save(path, "PNG")
    print(f"  {path}")

# 服務圖標
service_icons = {
    "jarvis": (59, 130, 246),   # blue
    "bridge": (6, 182, 212),    # cyan
    "vision": (16, 185, 129),   # green
}
for name, color in service_icons.items():
    icon = create_service_icon(name, color)
    path = os.path.join(ICONS_DIR, f"{name}.png")
    icon.save(path, "PNG")
    print(f"  {path}")

# 截圖
desktop = create_screenshot(1280, 720, "AI Service Portal - Desktop")
desktop.save(os.path.join(SCREENSHOTS_DIR, "desktop.png"), "PNG")
print(f"  {SCREENSHOTS_DIR}/desktop.png")

mobile = create_screenshot(750, 1334, "AI Service Portal - Mobile")
mobile.save(os.path.join(SCREENSHOTS_DIR, "mobile.png"), "PNG")
print(f"  {SCREENSHOTS_DIR}/mobile.png")

print("\nDone! All PWA assets generated.")
