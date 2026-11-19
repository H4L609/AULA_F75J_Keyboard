"""ビルドしたファームを確かめる（tools/build-f75j.ps1 から呼ばれる）。

1. 0xE000 にキー表の見出し "F75JKMAP" がある
2. ふつうのコードと定数（CSEG / CONST）が 0xE000 より手前で終わっている
3. keymap_gen.py が計算したキー表の数値が、コンパイラが作った数値と一致する
   （アプリはコンパイラを使わずに数値を書き込むので、ここが食い違うと困る）
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keymap_gen  # noqa: E402
import firmware_image  # noqa: E402
import config_store  # noqa: E402

ROOT = keymap_gen.ROOT
BUILD = keymap_gen.SMK / 'build'
HEX = BUILD / 'aula-f75j_default_smk.hex'
MAP = BUILD / 'aula-f75j_default_smk.map'


def main():
    errors = []
    img = firmware_image.FirmwareImage.load(HEX)

    if not img.has_config_store():
        errors.append('0xD000 に設定ファイルの場所の見出しがない')
    if not img.has_keymap_block():
        errors.append('0xE000 にキー表の見出しがない')

    text = MAP.read_text(encoding='utf-8', errors='replace')
    for area in ('CSEG', 'CONST', 'HOME', 'GSINIT', 'GSFINAL'):
        s = re.search(rf'C:\s+([0-9A-F]+)\s+s_{area}\b', text)
        ln = re.search(rf'C:\s+([0-9A-F]+)\s+l_{area}\b', text)
        if s and ln:
            end = int(s.group(1), 16) + int(ln.group(1), 16)
            if end > config_store.ADDR:
                errors.append(f'{area} が 0x{end:04X} まで伸びていて、設定ファイルの場所（0xD000）と重なる')

    data = json.loads(keymap_gen.SRC.read_text(encoding='utf-8'))
    _, values, enc, (mdir, msteps), light, tt = keymap_gen.generate(data, keymap_gen.load_names())
    if img.read_keymap() != keymap_gen.pack(values):
        errors.append('keymap_gen.py の数値と、コンパイラが作ったキー表が一致しない')
    if img.read_encoder() != keymap_gen.pack_encoder(enc):
        errors.append('keymap_gen.py の数値と、コンパイラが作ったノブの表が一致しない')
    if img.read_macros() != keymap_gen.pack_macros(mdir, msteps):
        errors.append('keymap_gen.py の数値と、コンパイラが作ったマクロの表が一致しない')
    if img.read_tapping_term() != tt:
        errors.append('keymap_gen.py の数値と、コンパイラが作ったタップの時間が一致しない')
    if img.read_light() != light:
        errors.append('keymap_gen.py の数値と、コンパイラが作ったライトの設定が一致しない')

    if errors:
        print('ファームのチェックで問題が見つかった:')
        print('\n'.join(errors))
        return 1
    print('ファームのチェック: 問題なし（キー表は 0xE000、ノブは 0xE670、マクロは 0xE690、ライトは 0xEBF0、設定ファイルは 0xD000、数値も一致）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
