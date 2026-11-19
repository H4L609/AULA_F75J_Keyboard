"""アプリのアイコン（app/icon.ico）を作る。Python の標準ライブラリだけで描く。

デザイン: 暗い地にキーボードを単純にした形。キーが 1 つだけ黄色く光る（案 B）。
小さいサイズ（24px 以下）では、キーを大きく少なくして、つぶれないようにする。
使い方: python tools/make_icon.py
"""
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'app' / 'icon.ico'
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]

EDGE = (0x3d, 0x44, 0x50)   # 地のふち（暗いタスクバーでも形がわかるように）
BG = (0x1e, 0x21, 0x27)     # 地
KEY = (0x4a, 0x51, 0x60)    # ふつうのキー
LIT = (0xf5, 0xb8, 0x3d)    # 光るキー


def layout(size):
    """(x, y, w, h, 角の丸み, 色) の並び。座標は 64 × 64 の中。"""
    shapes = [(3, 3, 58, 58, 14, EDGE), (4.5, 4.5, 55, 55, 12.5, BG)]
    if size <= 24:
        # 3 列 × 2 段の大きなキー。上の段の真ん中が光る
        for row, y in enumerate((16, 34)):
            for col, x in enumerate((9, 25.5, 42)):
                shapes.append((x, y, 13, 13, 3, LIT if (row, col) == (0, 1) else KEY))
    else:
        # 4 列 × 3 段。下の段の真ん中は横長（スペースキー）。上の段の 3 つ目が光る
        xs = (11, 22, 33, 44)
        for row, y in enumerate((17, 28, 39)):
            for col, x in enumerate(xs):
                if row == 2 and col == 2:
                    continue
                w = 20 if (row == 2 and col == 1) else 9
                shapes.append((x, y, w, 9, 2, LIT if (row, col) == (0, 2) else KEY))
    return shapes


def inside(px, py, x, y, w, h, r):
    if px < x or px > x + w or py < y or py > y + h:
        return False
    cx = min(max(px, x + r), x + w - r)
    cy = min(max(py, y + r), y + h - r)
    return (px - cx) ** 2 + (py - cy) ** 2 <= r * r


def render(size, ss=4):
    """4 × 4 の細かい点で塗って平均する（ふちをなめらかにする）。RGBA の行の並びを返す。"""
    shapes = layout(size)
    scale = 64 / size
    rows = []
    for j in range(size):
        row = bytearray()
        for i in range(size):
            acc = [0, 0, 0, 0]
            for sj in range(ss):
                for si in range(ss):
                    px = (i + (si + 0.5) / ss) * scale
                    py = (j + (sj + 0.5) / ss) * scale
                    col = None
                    for (x, y, w, h, r, c) in shapes:
                        if inside(px, py, x, y, w, h, r):
                            col = c
                    if col:
                        acc[0] += col[0]; acc[1] += col[1]; acc[2] += col[2]; acc[3] += 255
            n = ss * ss
            a = acc[3] / n
            if a:
                k = acc[3] / 255
                row += bytes((round(acc[0] / k), round(acc[1] / k), round(acc[2] / k), round(a)))
            else:
                row += b'\0\0\0\0'
        rows.append(bytes(row))
    return rows


def png(size, rows):
    raw = b''.join(b'\0' + r for r in rows)
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def main():
    images = [(s, png(s, render(s))) for s in SIZES]
    head = struct.pack('<HHH', 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b'', b''
    for s, img in images:
        entries += struct.pack('<BBBBHHII', s % 256, s % 256, 0, 0, 1, 32, len(img), offset + len(data))
        data += img
    OUT.write_bytes(head + entries + data)
    (ROOT / 'app' / 'icon-256.png').write_bytes(images[-1][1])  # 確認用
    print(f'{OUT} ({len(images)} サイズ)')


if __name__ == '__main__':
    main()
