"""キー配置（keymap.json）を、ファーム用のキー表に変換する。

2 つの使われ方がある。
  1. 開発用（この PC）: python tools/keymap_gen.py
       keymap/keymap.json → ファームのソースの keymap_user.h を書き出す（ビルドの初期値になる）
     python tools/keymap_gen.py --export-names
       キー名 → 数値 の対応表を app/keycodes.json に書き出す（アプリに同梱する）
     python tools/keymap_gen.py --check
       書き出さずに、keymap.json の中身を確かめるだけ
  2. アプリ（app/server.py）から: generate() で数値のキー表を作り、ファームに書き込む。
     アプリは app/keycodes.json を使うので、ファームのソースが無くても動く。

キー名の書き方は docs/keymap-guide.md を参照。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SMK = ROOT / 'third_party' / 'smk_aulaF75'
KB = SMK / 'src' / 'keyboards' / 'aula-f75j'
OUT = KB / 'layouts' / 'default' / 'keymap_user.h'
SRC = ROOT / 'keymap' / 'keymap.json'
NAMES_JSON = ROOT / 'app' / 'keycodes.json'

MAX_LAYERS = 8
MATRIX_ROWS, MATRIX_COLS = 6, 17
KC_TRANSPARENT = 0x0001

# keymap.json の 1 行の並び（左上から右へ）→ 内部の配線の位置（行, 列）。
# layout.c の LAYOUT_75_jis と同じ対応。
PHYS = [
    [(0, c) for c in [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]],
    [(1, c) for c in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 13, 14]],
    [(2, c) for c in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14]],
    [(3, c) for c in range(15)],
    [(4, c) for c in range(15)],
    [(5, c) for c in [0, 1, 2, 3, 5, 7, 8, 9, 12, 13, 14]],
]
ROW_LENGTHS = [len(r) for r in PHYS]

MODS = {
    'ctrl': 'LCTL', 'lctrl': 'LCTL', 'rctrl': 'RCTL',
    'shift': 'LSFT', 'lshift': 'LSFT', 'rshift': 'RSFT',
    'alt': 'LALT', 'lalt': 'LALT', 'ralt': 'RALT',
    'win': 'LGUI', 'lwin': 'LGUI', 'rwin': 'RGUI', 'gui': 'LGUI',
}
MOD_VALUE = {'LCTL': 0x0100, 'LSFT': 0x0200, 'LALT': 0x0400, 'LGUI': 0x0800,
             'RCTL': 0x1100, 'RSFT': 0x1200, 'RALT': 0x1400, 'RGUI': 0x1800}
QK_MOMENTARY = 0x5220
QK_MOD_TAP = 0x2000
QK_LAYER_TAP = 0x4000
# 同時押しやタップに使える「普通のキー」の範囲（KC_A 0x04 〜 KC_EXSEL 0xA4）。
# メディアキーなどは送り方がちがうので使えない。
BASIC_MIN, BASIC_MAX = 0x04, 0xA4

# 日本語配列向けの、わかりやすい別名
ALIASES = {
    'YEN': 'KC_INT3', '¥': 'KC_INT3', 'RO': 'KC_INT1', 'KANA': 'KC_INT2',
    'HENKAN': 'KC_INT4', 'MUHENKAN': 'KC_INT5', 'ZENKAKU': 'KC_GRV', 'HANZEN': 'KC_GRV',
    'FN': 'MO(1)', '___': '_______', 'NO': 'KC_NO',
    'CTRL': 'KC_LCTL', 'SHIFT': 'KC_LSFT', 'ALT': 'KC_LALT', 'WIN': 'KC_LGUI',
}


# ------------------------------------------------------------------ キー名の表

def names_from_source():
    """SMK のヘッダーを読んで、キー名 → 数値 の表を作る（開発用）。"""
    text = (SMK / 'src' / 'smk' / 'keycodes.h').read_text(encoding='utf-8', errors='replace')
    raw = dict(re.findall(r'^\s+([A-Z_][A-Z0-9_]*)\s*=\s*([A-Za-z0-9_]+)\s*,', text, re.M))
    raw.update(re.findall(r'^#define\s+(QK_[A-Z0-9_]+|SAFE_RANGE)\s+(0x[0-9A-Fa-f]+|[A-Z_][A-Z0-9_]*)\s*$', text, re.M))

    vals = {}

    def resolve(n, depth=0):
        if n in vals:
            return vals[n]
        v = raw[n]
        x = int(v, 0) if re.fullmatch(r'0x[0-9A-Fa-f]+|\d+', v) else resolve(v, depth + 1)
        vals[n] = x
        return x

    for n in raw:
        try:
            resolve(n)
        except (KeyError, RecursionError):
            pass

    # F75J 独自のキー（kbdef.h の enum custom_keycodes）: SAFE_RANGE から順番に
    kbdef = (KB / 'kbdef.h').read_text(encoding='utf-8', errors='replace')
    m = re.search(r'enum custom_keycodes\s*\{(.*?)\};', kbdef, re.S)
    body = re.sub(r'/\*.*?\*/', '', m.group(1), flags=re.S)
    body = re.sub(r'//[^\n]*', '', body)
    nxt = None
    for item in [i.strip() for i in body.split(',') if i.strip()]:
        if '=' in item:
            name, v = [x.strip() for x in item.split('=')]
            nxt = vals[v] if v in vals else int(v, 0)
        else:
            name = item
        vals[name] = nxt
        nxt += 1
    vals.pop('KB_SAFE_RANGE', None)
    assert vals['QK_MOMENTARY'] == QK_MOMENTARY and vals['KC_TRANSPARENT'] == KC_TRANSPARENT
    return {n: v for n, v in vals.items() if not n.endswith('_MAX') and n != 'SAFE_RANGE'}


def load_names():
    """キー名の表。ファームのソースがあればそこから、なければ app/keycodes.json から。"""
    if (SMK / 'src' / 'smk' / 'keycodes.h').exists():
        return names_from_source()
    return json.loads(NAMES_JSON.read_text(encoding='utf-8'))


def known_names(names=None):
    return set((names or load_names()).keys())


# ------------------------------------------------------------------ 変換

def basic(name, names):
    """1 つのキー名を (C の名前, 数値) にする。わからない名前なら None。"""
    n = name.strip()
    target = ALIASES.get(n.upper(), ALIASES.get(n))
    if target == 'MO(1)':
        return None
    for cand in ([target] if target else []) + [n, n.upper(), 'KC_' + n.upper()]:
        if cand in names:
            return cand, names[cand]
    return None


def convert(cell, names, layer):
    """keymap.json の 1 マスを (C の式, 数値, 使う層の番号 or None) にする。だめなら ValueError。"""
    if not isinstance(cell, str) or not cell.strip():
        raise ValueError('空のマスがある（何もしないなら "NO"、下の層と同じなら "___" と書く）')
    s = cell.strip()

    # タップと長押し: MT(修飾キー, タップのキー) / LT(層の番号, タップのキー)
    m = re.fullmatch(r'(MT|LT)\(\s*([^,]+?)\s*,\s*([^,]+?)\s*\)', s, re.I)
    if m:
        kind, hold, tap = m.group(1).upper(), m.group(2), m.group(3)
        b = basic(tap, names)
        if b is None:
            raise ValueError(f'{s}: タップのキー「{tap}」が見つからない')
        texpr, tval = b
        if not BASIC_MIN <= tval <= BASIC_MAX:
            raise ValueError(f'{s}: タップにできるのは普通のキーだけ（「{tap}」は使えない）')
        if kind == 'LT':
            if hold.strip() != '1':
                raise ValueError(f'{s}: 長押しで切り替えられるのは Fn 層（1 番）だけ')
            if layer != 0:
                raise ValueError(f'{s}: 長押しで層を切り替えるキーは、ベース層（0 番）にだけ置ける')
            n = int(hold)
            return f'(QK_LAYER_TAP | ({n} << 8) | {texpr})', QK_LAYER_TAP | (n << 8) | tval, n
        m5 = 0
        sides = set()
        for md in [p.strip() for p in hold.split('+')]:
            mm = MODS.get(md.lower())
            if mm is None:
                raise ValueError(f'{s}: 「{md}」は修飾キーとして使えない（Ctrl / Shift / Alt / Win）')
            m5 |= MOD_VALUE[mm] >> 8
            sides.add(mm[0])
        if len(sides) > 1:
            raise ValueError(f'{s}: 長押しの修飾キーに、左と右をまぜることはできない')
        return f'(QK_MOD_TAP | (0x{m5:02X} << 8) | {texpr})', QK_MOD_TAP | (m5 << 8) | tval, None

    m = re.fullmatch(r'MO\((\d+)\)', s, re.I)
    if m or s.upper() == 'FN':
        n = int(m.group(1)) if m else 1
        if layer != 0:
            raise ValueError(f'{s}: 層の切り替えはベース層（0 番）にだけ置ける')
        if n != 1:
            raise ValueError(f'{s}: 切り替えられるのは Fn 層（1 番）だけ')
        return f'MO({n})', QK_MOMENTARY | n, n

    if '+' in s and len(s) > 1:
        *mods, key = [p.strip() for p in s.split('+')]
        if MODS.get(key.lower()):  # 「Ctrl+Shift」のように修飾キーだけ
            mods, expr, val = mods + [key], 'KC_NO', 0
        else:
            b = basic(key, names)
            if b is None:
                raise ValueError(f'{s}: 「{key}」というキー名が見つからない')
            expr, val = b
            if not BASIC_MIN <= val <= BASIC_MAX:
                raise ValueError(f'{s}: 同時押しにできるのは普通のキーだけ（「{key}」は使えない）')
        for md in reversed(mods):
            mm = MODS.get(md.lower())
            if mm is None:
                raise ValueError(f'{s}: 「{md}」は修飾キーとして使えない（Ctrl / Shift / Alt / Win）')
            expr = f'{mm}({expr})'
            val |= MOD_VALUE[mm]
        return expr, val, None

    b = basic(s, names)
    if b is None:
        raise ValueError(f'「{s}」というキー名が見つからない')
    return b[0], b[1], None


LAYER_NAMES = ['base', 'fn', 'tap']
EMPTY = '___'
MAX_PROFILES = 4
DEFAULT_KNOB = {'base': ['VOLD', 'VOLU'], 'fn': [EMPTY, EMPTY]}  # [左回し, 右回し]


def _empty_rows():
    return [[EMPTY] * n for n in ROW_LENGTHS]


def _normalize_layers(layers):
    """層の並び → [base, fn, tap] の 3 つ。古い形（追加の層、ベースに直接書いた MT/LT）も直す。"""
    if not isinstance(layers, list) or not layers:
        raise ValueError('"layers" に層が 1 つもない')

    def rows_of(layer):
        rows = layer.get('keys') if isinstance(layer, dict) else None
        if not isinstance(rows, list) or len(rows) != len(PHYS) or \
                any(not isinstance(r, list) or len(r) != n for r, n in zip(rows, ROW_LENGTHS)):
            raise ValueError('層の形がちがう（6 行で、各行のキーの数は '
                             + ' / '.join(map(str, ROW_LENGTHS)) + '）')
        return [list(r) for r in rows]

    base = rows_of(layers[0])
    fn = _empty_rows()
    tap = _empty_rows()
    for li, layer in enumerate(layers[1:], start=1):
        name = layer.get('name') if isinstance(layer, dict) else None
        rows = rows_of(layer)
        if name == 'tap':
            tap = rows
        elif li == 1:
            fn = rows
        elif any(c != EMPTY for r in rows for c in r):
            raise ValueError(f'層 {li}（{name}）は使えなくなった（層は「ベース・Fn・タップ」の 3 つだけ）。'
                             '中身を Fn 層かタップ層に移してから消してください')

    # ベース層に直接書いた MT / LT を、ベース（長押し）とタップに分ける
    for ri, row in enumerate(base):
        for ki, cell in enumerate(row):
            m = re.fullmatch(r'(MT|LT)\(\s*([^,]+?)\s*,\s*([^,]+?)\s*\)', str(cell).strip(), re.I)
            if m and tap[ri][ki] == EMPTY:
                hold = m.group(2).strip()
                if m.group(1).upper() == 'LT':
                    hold = 'FN'
                elif MODS.get(hold.lower()):  # 修飾キー 1 つなら、正式な名前（LCTL など）にする
                    hold = MODS[hold.lower()]
                base[ri][ki] = hold
                tap[ri][ki] = m.group(3)
    return [{'name': n, 'keys': k} for n, k in zip(LAYER_NAMES, (base, fn, tap))]


def _normalize_knob(knob):
    out = {}
    for layer in ('base', 'fn'):
        v = (knob or {}).get(layer) if isinstance(knob, dict) else None
        if isinstance(v, list) and len(v) == 2 and all(isinstance(x, str) and x.strip() for x in v):
            out[layer] = [v[0].strip(), v[1].strip()]
        else:
            out[layer] = list(DEFAULT_KNOB[layer])
    return out


def normalize(data):
    """keymap.json を「プロファイル（最大 4）× [ベース・Fn・タップ] ＋ ノブ」の形にそろえる。

    古い形（profiles がなく layers だけ）は、プロファイル 1 つに直す。直せないときは ValueError。
    """
    if not isinstance(data, dict):
        raise ValueError('keymap.json の中身がちがう')
    if 'profiles' in data:
        profs = data['profiles']
        if not isinstance(profs, list) or not profs:
            raise ValueError('"profiles" にプロファイルが 1 つもない')
        if len(profs) > MAX_PROFILES:
            raise ValueError(f'プロファイルは {MAX_PROFILES} つまで')
    else:
        profs = [{'name': 'プロファイル 1', 'layers': data.get('layers'), 'knob': data.get('knob')}]
    out = []
    for pi, p in enumerate(profs):
        if not isinstance(p, dict):
            raise ValueError(f'プロファイル {pi + 1} の形がちがう')
        try:
            layers = _normalize_layers(p.get('layers'))
        except ValueError as e:
            raise ValueError(f'プロファイル {pi + 1}: {e}')
        name = p.get('name') if isinstance(p.get('name'), str) and p.get('name').strip() else f'プロファイル {pi + 1}'
        out.append({'name': name, 'layers': layers, 'knob': _normalize_knob(p.get('knob'))})
    return {'keyboard': data.get('keyboard', 'AULA F75J'), 'profiles': out,
            'macros': normalize_macros(data.get('macros')),
            'lighting': normalize_lighting(data.get('lighting')),
            'tapping_term': normalize_tapping_term(data.get('tapping_term'))}


def _hold_bits(val):
    """長押し側（ベース層の値）→ ('MT', 修飾の 5 ビット) / ('LT', 1) / None"""
    if val == QK_MOMENTARY | 1:
        return 'LT', 1
    if 0xE0 <= val <= 0xE7:  # 修飾キー 1 つ
        b = val & 0x07
        return 'MT', (0x10 if b >= 4 else 0) | (1 << (b & 3))
    if 0x0100 <= val <= 0x1FFF and (val & 0xFF) == 0:  # Ctrl+Shift のような修飾キーだけ
        return 'MT', (val >> 8) & 0x1F
    return None


def _profile_tables(prof, names, pname):
    """1 つのプロファイル → (exprs[2][R][C], values[2][R][C], enc_exprs[2][2], enc_values[2][2], errors)"""
    base, fn, tap = (L['keys'] for L in prof['layers'])
    errors = []
    exprs = [[['_______'] * MATRIX_COLS for _ in range(MATRIX_ROWS)] for _ in range(2)]
    values = [[[KC_TRANSPARENT] * MATRIX_COLS for _ in range(MATRIX_ROWS)] for _ in range(2)]
    for li in range(2):
        for r in range(MATRIX_ROWS):
            for c in range(MATRIX_COLS):
                if not any((r, c) in row for row in PHYS):  # 配線上にキーがない位置
                    exprs[li][r][c], values[li][r][c] = 'KC_NO', 0

    labels = {0: 'ベース層', 1: 'Fn 層'}
    for li, rows in ((0, base), (1, fn)):
        for ri, row in enumerate(rows):
            for ki, cell in enumerate(row):
                try:
                    expr, val, _ = convert(cell, names, li)
                    if li == 0 and val == KC_TRANSPARENT:
                        raise ValueError('ベース層に "___" は置けない（下の層がない）')
                    t = tap[ri][ki] if li == 0 else EMPTY
                    if t != EMPTY:
                        texpr, tval, _ = convert(t, names, 2)
                        if not BASIC_MIN <= tval <= BASIC_MAX:
                            raise ValueError(f'タップ層の「{t}」: タップにできるのは普通のキーだけ')
                        hb = _hold_bits(val)
                        if hb is None:
                            raise ValueError(f'タップ層に「{t}」があるので、ベース層（長押し）は'
                                             f'修飾キー（Ctrl など）か Fn にしてください（今は「{cell}」）')
                        if hb[0] == 'LT':
                            expr = f'(QK_LAYER_TAP | (1 << 8) | {texpr})'
                            val = QK_LAYER_TAP | (1 << 8) | tval
                        else:
                            expr = f'(QK_MOD_TAP | (0x{hb[1]:02X} << 8) | {texpr})'
                            val = QK_MOD_TAP | (hb[1] << 8) | tval
                    r, c = PHYS[ri][ki]
                    exprs[li][r][c], values[li][r][c] = expr, val
                except ValueError as e:
                    errors.append(f'{pname} {labels[li]} {ri + 1} 行目 {ki + 1} 個目: {e}')

    enc_exprs = [['KC_NO', 'KC_NO'], ['_______', '_______']]
    enc_values = [[0, 0], [KC_TRANSPARENT, KC_TRANSPARENT]]
    for li, lname in ((0, 'base'), (1, 'fn')):
        for d, dname in ((0, '左回し'), (1, '右回し')):
            cell = prof['knob'][lname][d]
            try:
                if re.fullmatch(r'(MO|MT|LT)\(.*\)|FN', cell.strip(), re.I):
                    raise ValueError('ノブに層の切り替えやタップと長押しは使えない')
                expr, val, _ = convert(cell, names, li)
                if li == 0 and val == KC_TRANSPARENT:
                    raise ValueError('ベース層のノブに "___" は置けない（何もしないなら "NO"）')
                enc_exprs[li][d], enc_values[li][d] = expr, val
            except ValueError as e:
                errors.append(f'{pname} {labels[li]} ノブ {dname}: {e}')
    return exprs, values, enc_exprs, enc_values, errors


def generate(data, names, light_id=0):
    """keymap.json の中身 → (C の初期化子の文字列, キー表 [8][R][C], ノブの表 [8][2])。だめなら ValueError。

    プロファイル p は、ファームの層 2p（ベース）と 2p+1（Fn）に入る。タップ層は、同じ位置の
    ベース層のキーと合わせて「タップと長押し」のキー（MT / LT）になる。使っていない
    プロファイルには、プロファイル 1 の中身を入れておく（切り替えても困らないように）。
    """
    data = normalize(data)
    profs = data['profiles']
    errors = []
    tables = []
    for pi, prof in enumerate(profs):
        t = _profile_tables(prof, names, f'プロファイル {pi + 1}')
        errors += t[4]
        tables.append(t)
    mdir_c, msteps_c, mdir, msteps, merr = generate_macros(data['macros'], names)
    errors += merr
    if errors:
        raise ValueError('\n'.join(errors))
    while len(tables) < MAX_PROFILES:
        tables.append(tables[0])

    exprs = [layer for t in tables for layer in t[0]]
    values = [layer for t in tables for layer in t[1]]
    enc_exprs = [row for t in tables for row in t[2]]
    enc_values = [row for t in tables for row in t[3]]

    lines = ['// このファイルは tools/keymap_gen.py が keymap/keymap.json から作ったもの。',
             '// 直接書き換えないこと（次のビルドで上書きされる）。',
             '#define KEYMAP_INIT { \\']
    for li in range(MAX_LAYERS):
        lines.append(f'    /* {li}: プロファイル {li // 2 + 1} {("base", "fn")[li % 2]} */ {{ \\')
        for r in range(MATRIX_ROWS):
            lines.append('        { ' + ', '.join(exprs[li][r]) + ' }, \\')
        lines.append('    }, \\')
    lines.append('}')
    lines.append('#define ENCODER_INIT { \\')
    for li in range(MAX_LAYERS):
        lines.append(f'    {{ {enc_exprs[li][0]}, {enc_exprs[li][1]} }}, \\')
    lines.append('}')
    lines.append(f'#define UMACRO_DIR_INIT {mdir_c}')
    lines.append(f'#define UMACRO_STEPS_INIT {msteps_c}')
    light = pack_light(data['lighting'], light_id)
    lines.append('#define LIGHT_INIT { ' + ', '.join(f'0x{x:02X}' for x in light) + ' }')
    tt = data['tapping_term']
    lines.append(f'#define TAPPING_TERM_MS {tt}')
    return '\n'.join(lines) + '\n', values, enc_values, (mdir, msteps), light, tt


# ------------------------------------------------------------------ マクロ

MACRO_COUNT = 16
MACRO_STEPS_MAX = 328
MACRO_MODES = {'once': 0, 'hold': 1, 'toggle': 2}
STEP_TYPES = {'tap': 1, 'press': 2, 'release': 3, 'delay': 4, 'text': None}

# 「文字を打つ」の変換表（パソコン側が日本語キーボードの設定のとき）。値は (キー名, Shift が要るか)
JIS_TEXT = {' ': ('SPC', False), '\n': ('ENT', False), '\t': ('TAB', False),
            '-': ('MINS', False), '=': ('MINS', True), '^': ('EQL', False), '~': ('EQL', True),
            '\\': ('INT3', False), '¥': ('INT3', False), '|': ('INT3', True),
            '@': ('LBRC', False), '`': ('LBRC', True), '[': ('RBRC', False), '{': ('RBRC', True),
            ';': ('SCLN', False), '+': ('SCLN', True), ':': ('QUOT', False), '*': ('QUOT', True),
            ']': ('BSLS', False), '}': ('BSLS', True), ',': ('COMM', False), '<': ('COMM', True),
            '.': ('DOT', False), '>': ('DOT', True), '/': ('SLSH', False), '?': ('SLSH', True),
            '_': ('INT1', True),
            '!': ('1', True), '"': ('2', True), '#': ('3', True), '$': ('4', True), '%': ('5', True),
            '&': ('6', True), "'": ('7', True), '(': ('8', True), ')': ('9', True)}


def _text_keys(text, names):
    """文字列 → 叩くキーの数値の並び。打てない文字があれば ValueError。"""
    out = []
    for ch in text:
        if 'a' <= ch <= 'z':
            key, shift = ch.upper(), False
        elif 'A' <= ch <= 'Z':
            key, shift = ch, True
        elif '0' <= ch <= '9':
            key, shift = ch, False
        elif ch in JIS_TEXT:
            key, shift = JIS_TEXT[ch]
        else:
            raise ValueError(f'「{ch}」は打てない（英数字と記号だけ。日本語は打てない）')
        _, val = basic(key, names)
        out.append(val | (MOD_VALUE['LSFT'] if shift else 0))
    return out


def normalize_macros(macros):
    """マクロの欄をそろえる。[{name, mode, steps: [[種類, 値], ...]}]（最大 16）"""
    if macros is None:
        return []
    if not isinstance(macros, list):
        raise ValueError('"macros" の形がちがう')
    if len(macros) > MACRO_COUNT:
        raise ValueError(f'マクロは {MACRO_COUNT} 個まで')
    out = []
    for i, m in enumerate(macros):
        if not isinstance(m, dict):
            raise ValueError(f'マクロ {i + 1} の形がちがう')
        name = m.get('name') if isinstance(m.get('name'), str) and m.get('name').strip() else f'マクロ {i + 1}'
        mode = m.get('mode') if m.get('mode') in MACRO_MODES else 'once'
        steps = []
        for st in m.get('steps') or []:
            if isinstance(st, list) and len(st) == 2 and st[0] in STEP_TYPES:
                steps.append([st[0], st[1]])
            else:
                raise ValueError(f'マクロ {i + 1}（{name}）: 手順の形がちがう: {st}')
        out.append({'name': name, 'mode': mode, 'steps': steps})
    return out


def generate_macros(macros, names):
    """マクロの欄 → (dir の C 初期化子, steps の C 初期化子, dir 数値, steps 数値, errors)"""
    errors = []
    dir_vals = [[0, 0] for _ in range(MACRO_COUNT)]
    steps = []
    for i, m in enumerate(macros):
        start = len(steps)
        dir_vals[i] = [start, MACRO_MODES[m['mode']]]
        where = f'マクロ {i + 1}（{m["name"]}）'
        for si, (kind, value) in enumerate(m['steps']):
            try:
                if kind == 'delay':
                    ms = int(value)
                    if not 1 <= ms <= 60000:
                        raise ValueError('待ち時間は 1〜60000 ms')
                    steps.append([4, ms])
                elif kind == 'text':
                    if not isinstance(value, str) or not value:
                        raise ValueError('文字が空')
                    steps += [[1, v] for v in _text_keys(value, names)]
                else:
                    if not isinstance(value, str) or re.fullmatch(r'(MO|MT|LT)\(.*\)|FN|MACRO_\d+|BOOT_HOLD', value.strip(), re.I):
                        raise ValueError(f'「{value}」はマクロの中では使えない')
                    _, val, _ = convert(value, names, 1)
                    if val in (0, KC_TRANSPARENT):
                        raise ValueError('キーが空')
                    steps.append([STEP_TYPES[kind], val])
            except ValueError as e:
                errors.append(f'{where} の {si + 1} 番目の手順: {e}')
        steps.append([0, 0])  # 終わり
    if len(steps) > MACRO_STEPS_MAX:
        errors.append(f'マクロの手順が多すぎる（全部で {len(steps)} 個。{MACRO_STEPS_MAX} 個まで。「文字を打つ」は 1 文字 = 1 個）')
    steps += [[0, 0]] * (MACRO_STEPS_MAX - len(steps))
    dir_c = '{ ' + ', '.join(f'{{ {a}, {b} }}' for a, b in dir_vals) + ' }'
    steps_c = '{ ' + ', '.join(f'{{ {a}, 0x{b:04X} }}' for a, b in steps[:MACRO_STEPS_MAX]) + ' }'
    return dir_c, steps_c, dir_vals, steps[:MACRO_STEPS_MAX], errors


def pack_macros(dir_vals, steps):
    """マクロの表 → ファームに書き込むバイト列（0xE690 から: dir 64 バイト + steps）。"""
    out = bytearray()
    for a, b in list(dir_vals) + list(steps):
        out += bytes((a & 0xFF, a >> 8, b & 0xFF, b >> 8))
    return bytes(out)


# ------------------------------------------------------------------ ライト

# エディタで選んだライトの設定。ファームの 0xEBF0 に入り、書き込み後に一度だけ反映される。
LIGHT_EFFECTS = 16   # 0〜14 が光り方、15 が消灯
LIGHT_LEVELS = {'effect': 16, 'brightness': 10, 'speed': 5, 'color': 8, 'direction': 2}
DEFAULT_LIGHTING = {'apply': False, 'effect': 10, 'brightness': 9, 'speed': 2, 'color': 7, 'direction': 0}


def normalize_lighting(light):
    out = dict(DEFAULT_LIGHTING)
    if isinstance(light, dict):
        if isinstance(light.get('apply'), bool):
            out['apply'] = light['apply']
        for k, n in LIGHT_LEVELS.items():
            v = light.get(k)
            if isinstance(v, int) and 0 <= v < n:
                out[k] = v
    return out


def pack_light(light, light_id):
    """ライトの設定 → 0xEBF0 の 16 バイト。light_id は書き込みごとの番号（0 なら反映しない）。"""
    lt = normalize_lighting(light)
    b = bytearray(16)
    b[0], b[1], b[2] = ord('L'), 1, 1 if lt['apply'] else 0
    b[3], b[4], b[5], b[6], b[7] = lt['effect'], lt['brightness'], lt['speed'], lt['color'], lt['direction']
    b[8], b[9] = light_id & 0xFF, (light_id >> 8) & 0xFF
    return bytes(b)


# ------------------------------------------------------------------ タップの時間

DEFAULT_TAPPING_TERM = 200


def normalize_tapping_term(v):
    return v if isinstance(v, int) and 100 <= v <= 1000 else DEFAULT_TAPPING_TERM


def pack_encoder(enc_values):
    """ノブの表 → ファームに書き込むバイト列（リトルエンディアン）。"""
    out = bytearray()
    for row in enc_values:
        for v in row:
            out += bytes((v & 0xFF, v >> 8))
    return bytes(out)


def pack(values):
    """数値のキー表 → ファームに書き込むバイト列（リトルエンディアン）。"""
    out = bytearray()
    for layer in values:
        for row in layer:
            for v in row:
                out += bytes((v & 0xFF, v >> 8))
    return bytes(out)


# ------------------------------------------------------------------ 開発用の入口

def main():
    names = load_names()
    if '--export-names' in sys.argv:
        NAMES_JSON.write_text(json.dumps(dict(sorted(names.items())), ensure_ascii=False, indent=0),
                              encoding='utf-8')
        print(f'書き出し: {NAMES_JSON.relative_to(ROOT)}（{len(names)} 個）')
        return 0
    try:
        data = json.loads(SRC.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f'keymap.json の書き方がまちがっている: {e}')
        return 1
    try:
        text = generate(data, names)[0]
    except ValueError as e:
        print('キー配置にまちがいがある:')
        print(e)
        return 1
    if '--check' in sys.argv:
        print('キー配置に問題なし')
        return 0
    OUT.write_text(text, encoding='utf-8', newline='\n')
    print(f'書き出し: {OUT.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
