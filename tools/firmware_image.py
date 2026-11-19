"""ファーム（Intel HEX）を読み書きし、0xE000 のキー表を差し替える。

アプリ（app/server.py）と、開発用のチェック（tools/check_layout.py）の両方が使う。
HEX の各行（レコード）はそのまま残し、キー表の範囲のバイトだけを書き換えて、
行ごとの確認用の値（チェックサム）を計算し直す。ほかの場所には一切触れない。
"""
from pathlib import Path

KEYMAP_HEADER_ADDR = 0xE000
KEYMAP_DATA_ADDR = 0xE010
MAGIC = b'F75JKMAP'
LAYERS, ROWS, COLS = 8, 6, 17
KEYMAP_SIZE = LAYERS * ROWS * COLS * 2  # 1632
ENCODER_ADDR = KEYMAP_DATA_ADDR + KEYMAP_SIZE  # 0xE670
ENCODER_SIZE = LAYERS * 2 * 2  # [層][左回し, 右回し] × 2 バイト = 32
MACRO_ADDR = ENCODER_ADDR + ENCODER_SIZE  # 0xE690
MACRO_SIZE = (16 + 328) * 4  # dir 16 個 + 手順 328 個、各 4 バイト（0xEBEF まで）
LIGHT_ADDR = MACRO_ADDR + MACRO_SIZE  # 0xEBF0
LIGHT_SIZE = 16
VERSION = 4
PROFILES = 4
MACROS = 16


class FirmwareImage:
    def __init__(self, records):
        # records: [[type, addr, bytearray]]（HEX の 1 行ずつ）
        self.records = records

    @classmethod
    def load(cls, path):
        recs = []
        for line in Path(path).read_text(encoding='ascii').splitlines():
            line = line.strip()
            if not line:
                continue
            if not line.startswith(':'):
                raise ValueError('HEX ファイルではない')
            b = bytes.fromhex(line[1:])
            n, addr, typ = b[0], (b[1] << 8) | b[2], b[3]
            if (sum(b) & 0xFF) != 0:
                raise ValueError(f'HEX のチェックサムが合わない: {line}')
            if typ not in (0, 1):
                raise ValueError('対応していない HEX の形式（拡張アドレス）')
            recs.append([typ, addr, bytearray(b[4:4 + n])])
        return cls(recs)

    def read(self, addr, size):
        out = bytearray(size)
        seen = bytearray(size)
        for typ, a, data in self.records:
            if typ != 0:
                continue
            for i, v in enumerate(data):
                j = a + i - addr
                if 0 <= j < size:
                    out[j] = v
                    seen[j] = 1
        if not all(seen):
            raise ValueError(f'0x{addr:04X} からの {size} バイトが HEX の中にない')
        return bytes(out)

    def write(self, addr, payload):
        size = len(payload)
        self.read(addr, size)  # 範囲が全部あることを先に確かめる
        for typ, a, data in self.records:
            if typ != 0:
                continue
            for i in range(len(data)):
                j = a + i - addr
                if 0 <= j < size:
                    data[i] = payload[j]

    def has_keymap_block(self):
        try:
            h = self.read(KEYMAP_HEADER_ADDR, 16)
        except ValueError:
            return False
        return h[:8] == MAGIC and h[8] == VERSION and (h[9], h[10], h[11], h[12], h[13]) == (ROWS, COLS, LAYERS, PROFILES, MACROS)

    def read_keymap(self):
        return self.read(KEYMAP_DATA_ADDR, KEYMAP_SIZE)

    def read_encoder(self):
        return self.read(ENCODER_ADDR, ENCODER_SIZE)

    def read_macros(self):
        return self.read(MACRO_ADDR, MACRO_SIZE)

    def read_light(self):
        return self.read(LIGHT_ADDR, LIGHT_SIZE)

    def read_tapping_term(self):
        h = self.read(KEYMAP_HEADER_ADDR, 16)
        return h[14] | (h[15] << 8)

    def has_config_store(self):
        import config_store
        try:
            return self.read(config_store.ADDR, 8) == config_store.MAGIC
        except ValueError:
            return False

    def read_config(self):
        """キーボードに保存した設定ファイル（dict）。なければ None。"""
        import config_store
        try:
            return config_store.unpack(self.read(config_store.ADDR, config_store.SIZE))
        except ValueError:
            return None

    def write_config(self, blob):
        import config_store
        if len(blob) != config_store.SIZE or not self.has_config_store():
            raise ValueError('このファームには設定ファイルの場所（0xD000）がない')
        self.write(config_store.ADDR, blob)

    def write_keymap(self, payload, encoder, macros, light, tapping_term):
        if len(payload) != KEYMAP_SIZE or len(encoder) != ENCODER_SIZE or len(macros) != MACRO_SIZE \
                or len(light) != LIGHT_SIZE:
            raise ValueError('キー表の大きさがちがう')
        if not self.has_keymap_block():
            raise ValueError('このファームにはキー表の場所（0xE000、第 4 版）がない')
        self.write(KEYMAP_DATA_ADDR, payload)
        self.write(ENCODER_ADDR, encoder)
        self.write(MACRO_ADDR, macros)
        self.write(LIGHT_ADDR, light)
        self.write(KEYMAP_HEADER_ADDR + 14, bytes((tapping_term & 0xFF, tapping_term >> 8)))

    def save(self, path):
        lines = []
        for typ, a, data in self.records:
            b = bytes((len(data), a >> 8, a & 0xFF, typ)) + bytes(data)
            lines.append(':' + (b + bytes(((-sum(b)) & 0xFF,))).hex().upper())
        Path(path).write_text('\n'.join(lines) + '\n', encoding='ascii')
