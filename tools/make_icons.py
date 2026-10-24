"""生成 Android 启动图标（自适应图标 + 各密度位图）。

用法（需要 Pillow）：
    python tools/make_icons.py
"""
import os
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'web', 'assets', 'img_29ee47be744b.png')  # 骑士头像
RES = os.path.join(ROOT, 'android', 'res')

GOLD = (255, 176, 32, 255)
GOLD_SOFT = (255, 190, 70, 255)


def vertical_gradient(size, top, bottom):
    w, h = size
    img = Image.new('RGBA', size)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        for x in range(w):
            px[x, y] = c
    return img


def radial_glow(size, center, radius, color):
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    steps = 40
    for i in range(steps, 0, -1):
        r = radius * i / steps
        alpha = int(color[3] * (1 - i / steps) ** 1.6)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color[:3] + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(radius / 12.0))


def build_background(size=432):
    img = vertical_gradient((size, size), (27, 37, 71), (7, 11, 24))
    img = Image.alpha_composite(img, radial_glow((size, size), (size * 0.3, size * 0.22), size * 0.75, (255, 176, 32, 60)))
    img = Image.alpha_composite(img, radial_glow((size, size), (size * 0.78, size * 0.85), size * 0.7, (176, 107, 255, 45)))
    return img


def build_foreground(size=432):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size // 2
    # 金色外环
    ring_r = size * 0.315
    d.ellipse([c - ring_r, c - ring_r, c + ring_r, c + ring_r], outline=GOLD, width=max(2, size // 54))
    # 环内微光
    img = Image.alpha_composite(img, radial_glow((size, size), (c, c), ring_r * 0.95, (255, 176, 32, 42)))
    d = ImageDraw.Draw(img)
    d.ellipse([c - ring_r, c - ring_r, c + ring_r, c + ring_r], outline=GOLD, width=max(2, size // 54))
    # 骑士头像（放大 2x 再缩到目标尺寸，保持像素块清晰）
    art_px = int(size * 0.52)
    art = Image.open(SRC).convert('RGBA')
    art = art.resize((art_px, art_px), Image.LANCZOS)
    img.alpha_composite(art, (c - art_px // 2, c - art_px // 2))
    return img


def legacy_icon(size):
    bg = build_background(size)
    fg = build_foreground(size)
    icon = Image.alpha_composite(bg, fg)
    # 圆角矩形遮罩（22% 圆角，符合 Android 旧版图标观感）
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=255)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(icon, (0, 0), mask)
    return out


def round_icon(size):
    bg = build_background(size)
    fg = build_foreground(size)
    icon = Image.alpha_composite(bg, fg)
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(icon, (0, 0), mask)
    return out


def save(img, rel):
    path = os.path.join(RES, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, 'PNG', optimize=True)
    print('wrote', rel, img.size)


def main():
    save(build_background(432), os.path.join('drawable-nodpi', 'ic_launcher_bg.png'))
    save(build_foreground(432), os.path.join('drawable-nodpi', 'ic_launcher_fg.png'))
    densities = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
    for d, px in densities.items():
        save(legacy_icon(px), os.path.join('mipmap-' + d, 'ic_launcher.png'))
        save(round_icon(px), os.path.join('mipmap-' + d, 'ic_launcher_round.png'))


if __name__ == '__main__':
    main()
