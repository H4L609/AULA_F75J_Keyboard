"""キーボードの中に置く「設定ファイル」（0xD000〜0xDFFF の 4KB）を作る・読む。

エディタの設定（keymap.json の中身すべて）を、圧縮してファームに入れておく。
別の PC のエディタでも「キーボードから読み込む」で、名前なども含めて元に戻せる。

  0xD000  "F75JCONF"（8）, 版 1, 予備 1, 長さ（2、LE）, CRC32（4、LE）, 圧縮した JSON（最大 4080）

JSON の中身:
  {"format": "f75j-config", "version": 1, "written_at": "...", "app_version": "...",
   "hash": "<設定の指紋>", "keymap": <keymap.json の中身（そろえたもの）>}
"""
import hashlib
import json
import zlib

ADDR = 0xD000
SIZE = 4096
HEADER = 16
MAGIC = b'F75JCONF'
VERSION = 1


def config_hash(normalized):
    """設定の指紋（そろえた keymap.json の中身から計算する。同じ内容なら同じ値）。"""
    text = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def pack(normalized, written_at, app_version):
    """設定 → 4096 バイト。入りきらないときは ValueError。"""
    doc = {'format': 'f75j-config', 'version': 1, 'written_at': written_at, 'app_version': app_version,
           'hash': config_hash(normalized), 'keymap': normalized}
    raw = json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    body = zlib.compress(raw, 9)
    if len(body) > SIZE - HEADER:
        raise ValueError(f'設定が大きすぎて、キーボードに保存できません（圧縮して {len(body)} バイト。'
                         f'{SIZE - HEADER} バイトまで）。マクロや使っていないプロファイルを減らしてください')
    out = bytearray(SIZE)
    out[0:8] = MAGIC
    out[8] = VERSION
    out[10:12] = len(body).to_bytes(2, 'little')
    out[12:16] = (zlib.crc32(body) & 0xFFFFFFFF).to_bytes(4, 'little')
    out[HEADER:HEADER + len(body)] = body
    return bytes(out)


def unpack(blob):
    """4096 バイト → JSON の中身（dict）。保存されていない・壊れているときは None。"""
    if len(blob) < HEADER or blob[0:8] != MAGIC or blob[8] != VERSION:
        return None
    n = int.from_bytes(blob[10:12], 'little')
    if n == 0 or HEADER + n > len(blob):
        return None
    body = bytes(blob[HEADER:HEADER + n])
    if (zlib.crc32(body) & 0xFFFFFFFF) != int.from_bytes(blob[12:16], 'little'):
        return None
    try:
        doc = json.loads(zlib.decompress(body).decode('utf-8'))
    except (zlib.error, ValueError):
        return None
    return doc if isinstance(doc, dict) and doc.get('format') == 'f75j-config' else None
