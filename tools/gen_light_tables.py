"""ファームのライトの表を、自分のキー配置と数式から作る。

出荷時のファームから写した表を使わないためのもの。表はすべて、次の 2 つだけから作る。
  - キーの位置: このプロジェクトのキー配置（app/index.html の PHYS と同じ並び）と、
    各キーの配線上の位置（docs/f75j-matrix.md）
  - 色や明るさの変化: このファイルに書いた数式

書き出すファイル（third_party/smk_aulaF75/src/keyboards/aula-f75j/）:
  - aula_fx_tables.h   … aula_fx.c が使う表
  - aula_rgb_wheel.h   … aula_rgb.c が使う色の輪
使い方: python tools/gen_light_tables.py
"""
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'third_party' / 'smk_aulaF75' / 'src' / 'keyboards' / 'aula-f75j'

COLS, ROWS = 17, 6

# ------------------------------------------------------------------ キー配置
# 行ごとに (名前, 幅, 前の空き, 配線の列)。幅と空きの単位はキー 1 個分。行の番号は配線の行と同じ。
LAYOUT = [
    [('Esc', 1, 0, 0), ('F1', 1, .5, 2), ('F2', 1, 0, 3), ('F3', 1, 0, 4), ('F4', 1, 0, 5),
     ('F5', 1, .25, 6), ('F6', 1, 0, 7), ('F7', 1, 0, 8), ('F8', 1, 0, 9),
     ('F9', 1, .25, 10), ('F10', 1, 0, 11), ('F11', 1, 0, 12), ('F12', 1, 0, 13), ('Knob', 1, .75, 14)],
    [('Zenkaku', 1, 0, 0)] + [(str((i + 1) % 10), 1, 0, i + 1) for i in range(10)] +
    [('-', 1, 0, 11), ('^', 1, 0, 12), ('Yen', 1, 0, 16), ('BS', 1, 0, 13), ('Del', 1, 0, 14)],
    [('Tab', 1.5, 0, 0)] + [(k, 1, 0, i + 1) for i, k in enumerate('QWERTYUIOP')] +
    [('@', 1, 0, 11), ('[', 1, 0, 12), ('PgUp', 1, 1.5, 14)],
    [('Caps', 1.75, 0, 0)] + [(k, 1, 0, i + 1) for i, k in enumerate('ASDFGHJKL')] +
    [(';', 1, 0, 10), (':', 1, 0, 11), (']', 1, 0, 12), ('Enter', 1.25, 0, 13), ('PgDn', 1, 0, 14)],
    [('LShift', 1.25, 0, 0)] + [(k, 1, 0, i + 1) for i, k in enumerate('ZXCVBNM,./')] +
    [('Ro', 1, 0, 11), ('RShift', 1.75, 0, 12), ('Up', 1, 0, 13), ('End', 1, 0, 14)],
    [('LCtrl', 1.25, 0, 0), ('Win', 1.25, 0, 1), ('Alt', 1.25, 0, 2), ('Muhenkan', 1.25, 0, 3),
     ('Space', 4.5, 0, 5), ('Henkan', 1.25, 0, 7), ('Kana', 1.25, 0, 8), ('Fn', 1, 0, 9),
     ('Left', 1, 0, 12), ('Down', 1, 0, 13), ('Right', 1, 0, 14)],
]

# 配線の (列, 行) → (名前, 中心の x, 中心の y)
KEYS = {}
for row, keys in enumerate(LAYOUT):
    x = 0.0
    for name, w, gap, col in keys:
        x += gap
        KEYS[(col, row)] = (name, x + w / 2, row + 0.5)
        x += w
WIDTH = max(cx for _, cx, _ in KEYS.values()) + 0.5
CENTER = (WIDTH / 2, ROWS / 2)


def present(col, row):
    return (col, row) in KEYS


# ------------------------------------------------------------------ 数式
def channel(t):
    """0〜1 → 0〜255。明るさの変わり方を人の目に合わせて、立ち上がりをゆるやかにする（2 乗）。"""
    return round(255 * max(0.0, min(1.0, t)) ** 2)


def hue_rgb(h):
    """色相 h（0〜1、赤 → 黄 → 緑 → 水色 → 青 → 紫 → 赤）を (R, G, B) にする。"""
    h = (h % 1.0) * 6
    sector, f = int(h), h - int(h)
    up, down = channel(f), channel(1 - f)
    return [(255, up, 0), (down, 255, 0), (0, 255, up),
            (0, down, 255), (up, 0, 255), (255, 0, down)][sector]


def wheel(n=192):
    """色の輪（aula_rgb.c）: 赤から始めて、色相を一周する。"""
    return [hue_rgb(i / n) for i in range(n)]


def palette(n=128):
    """グラデーション（流れる波で使う）: 青から始めて、色相を逆回りに一周する。"""
    return [hue_rgb(2 / 3 - i / n) for i in range(n)]


def breath(n=96, floor=20):
    """呼吸: いちばん暗い floor から 255 まで、余弦の形でなめらかに上がって下がる。"""
    return [round(floor + (255 - floor) * (1 - math.cos(2 * math.pi * i / n)) / 2) for i in range(n)]


COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 255)]


def key_id_table():
    """配線の (列, 行) → 「見た目の列 * 8 + 行」。キーがなければ 0xFF。
    見た目の列 = キーの中心が左から何キー目にあるか（0〜16）。¥ のように配線と見た目の順番が
    違うキーも、見た目の左右の並びで流れるようにする。"""
    t = [[0xFF] * ROWS for _ in range(COLS)]
    for (col, row), (_, cx, _) in KEYS.items():
        vcol = max(0, min(COLS - 1, int(cx)))
        t[col][row] = vcol * 8 + row
    return t


def rings(n_rings=9, slots=13):
    """波紋: キーボードの真ん中からの距離で、内側から順に輪に分ける。中身は「配線の列 * 8 + 行」。
    輪の数と 1 つの輪に入る数には上限があるので、入りきらないキーは次の輪に回す。"""
    keys = sorted(KEYS.items(), key=lambda kv: math.hypot(kv[1][1] - CENTER[0], (kv[1][2] - CENTER[1]) * 1.0))
    far = max(math.hypot(cx - CENTER[0], cy - CENTER[1]) for _, cx, cy in KEYS.values())
    out = [[] for _ in range(n_rings)]
    for (col, row), (_, cx, cy) in keys:
        r = min(n_rings - 1, int(math.hypot(cx - CENTER[0], cy - CENTER[1]) / far * n_rings))
        while r < n_rings and len(out[r]) >= slots:
            r += 1
        if r < n_rings:
            out[r].append(col * 8 + row)
    placed = sum(len(x) for x in out)
    return [x + [0xFF] * (slots - len(x)) for x in out], placed


def keywave_table():
    """流れる波: キーボードの真ん中のまわりの角度（0〜127）。グラデーションが回るように見える。"""
    t = [[0] * ROWS for _ in range(COLS)]
    for col in range(COLS):
        for row in range(ROWS):
            if present(col, row):
                _, cx, cy = KEYS[(col, row)]
            else:
                cx, cy = col + 0.5, row + 0.5
            a = math.atan2(cy - CENTER[1], (cx - CENTER[0]) / 3)  # 横長なので、横を縮めて角度を均す
            t[col][row] = round((a / (2 * math.pi)) * 128) % 128
    return t


def shimmer_tables():
    """きらめき: 上の 3 行は左から右へ、下の 3 行は右から左へ、位置に応じて光る時期をずらす。
    虹色用（0〜191）と単色用（0〜95）の 2 つ。"""
    wheel_t = [[0] * ROWS for _ in range(COLS)]
    fixed_t = [[0] * ROWS for _ in range(COLS)]
    for col in range(COLS):
        for row in range(ROWS):
            cx = KEYS[(col, row)][1] if present(col, row) else col + 0.5
            f = cx / WIDTH
            if row >= ROWS // 2:
                f = 1 - f
            wheel_t[col][row] = int(f * 192) % 192
            fixed_t[col][row] = int(f * 96) % 96
    return wheel_t, fixed_t


def gaming_table():
    """ゲーミング: Esc、W A S D、矢印のキーだけ光る（列ごとに、行のビットを立てる）。"""
    lit = {'Esc', 'W', 'A', 'S', 'D', 'Up', 'Left', 'Down', 'Right'}
    t = [0] * COLS
    for (col, row), (name, _, _) in KEYS.items():
        if name in lit:
            t[col] |= 1 << row
    return t


def present_table():
    t = [0] * COLS
    for (col, row) in KEYS:
        t[col] |= 1 << row
    return t


# ------------------------------------------------------------------ 書き出し
HEAD = ('/* このファイルは tools/gen_light_tables.py が作ったもの。手で直さないこと。\n'
        ' * 表は、プロジェクトのキー配置と数式だけから作っている（出荷時のファームは使わない）。 */\n')


def rgb_rows(name, size_macro, data, per_line=4):
    lines = [f'static const __code uint8_t {name}[{size_macro}][3] = {{']
    for i in range(0, len(data), per_line):
        lines.append('    ' + ' '.join('{%3d,%3d,%3d},' % c for c in data[i:i + per_line]))
    return '\n'.join(lines) + '\n};\n'


def grid(name, data, cols_macro='AULA_FX_COLS', rows_macro='AULA_FX_ROWS', fmt='%3d'):
    lines = [f'static const __code uint8_t {name}[{cols_macro}][{rows_macro}] = {{']
    for c, row in enumerate(data):
        lines.append('    {' + ', '.join(fmt % v for v in row) + f'}}, /* 列 {c:2d} */')
    return '\n'.join(lines) + '\n};\n'


def flat(name, size, data, fmt='0x%02x', per_line=17):
    lines = [f'static const __code uint8_t {name}[{size}] = {{']
    for i in range(0, len(data), per_line):
        lines.append('    ' + ', '.join(fmt % v for v in data[i:i + per_line]) + ',')
    return '\n'.join(lines) + '\n};\n'


def main():
    rg, placed = rings()
    sw, sf = shimmer_tables()
    fx = [HEAD, '#pragma once\n', '#include <stdint.h>\n',
          '/* 7 つの単色: 赤・緑・青・黄・紫・水色・白 */\n',
          rgb_rows('colors', 'AULA_FX_COLOR_MODES - 1', COLORS),
          '/* グラデーション: 青から色相を逆回りに一周（128 色） */\n',
          rgb_rows('palette', 'AULA_FX_PALETTE_SIZE', palette()),
          f'/* 波紋: 真ん中からの距離で分けた輪（配線の列 * 8 + 行、0xff は空き）。{placed} キーを配置 */\n',
          'static const __code uint8_t rings[AULA_FX_RINGS][AULA_FX_RING_SLOTS] = {\n' +
          '\n'.join('    {' + ', '.join('0x%02x' % v for v in r) + '},' for r in rg) + '\n};\n',
          '/* キーがある行のビット（列ごと） */\n', flat('present', 'AULA_FX_COLS', present_table()),
          '/* 配線の (列, 行) → 見た目の列 * 8 + 行（0xff はキーなし） */\n',
          grid('key_id', key_id_table(), fmt='0x%02x'),
          '/* ゲーミング: Esc、W A S D、矢印（列ごとの行のビット） */\n', flat('gaming', 'AULA_FX_COLS', gaming_table()),
          '/* 流れる波: 真ん中のまわりの角度（0〜127） */\n', grid('keywave', keywave_table()),
          '/* きらめき（虹色、0〜191）: 上 3 行は左から、下 3 行は右から */\n', grid('shimmer_wheel', sw),
          '/* きらめき（単色、0〜95） */\n', grid('shimmer_fixed', sf),
          '/* 呼吸: 20 → 255 → 20（余弦の形） */\n', flat('breath', 'AULA_FX_BREATH_SIZE', breath(), fmt='%3d', per_line=16)]
    (OUT_DIR / 'aula_fx_tables.h').write_text('\n'.join(fx), encoding='utf-8', newline='\n')
    rgb = [HEAD, '#pragma once\n', '#include <stdint.h>\n',
           '/* 色の輪: 赤から色相を一周（192 色）。明るさの立ち上がりは 2 乗でゆるやかにしている */\n',
           rgb_rows('wheel', 'AULA_RGB_WHEEL_SIZE', wheel())]
    (OUT_DIR / 'aula_rgb_wheel.h').write_text('\n'.join(rgb), encoding='utf-8', newline='\n')
    print(f'aula_fx_tables.h / aula_rgb_wheel.h を書き出した（波紋に {placed} / {len(KEYS)} キー）')


if __name__ == '__main__':
    main()
