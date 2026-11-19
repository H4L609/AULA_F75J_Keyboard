"""AULA F75J キー配置エディタ（PC の中だけで動く Web アプリ）。

しくみ:
  - 画面（index.html）でキー配置を編集し、keymap.json に保存する。
  - 「書き込む」で、同梱のファーム（firmware-base.hex）の 0xE000 のキー表だけを
    差し替え、同梱の sinowisp.exe でキーボードに書き込む。
  - コンパイラなどは使わないので、使う人の PC に環境構築は要らない。

起動（開発中）: python app/server.py
配布用: tools/package.ps1 で 1 つの exe とインストーラーにまとめる。
"""
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FROZEN = getattr(sys, 'frozen', False)
if FROZEN:
    RES = Path(sys._MEIPASS)  # exe に同梱したファイルの置き場所
    DATA = Path(os.environ.get('APPDATA', Path.home())) / 'AULA F75J Keymap'
    KEYMAP = DATA / 'keymap.json'
    SINOWISP = RES / 'sinowisp.exe'
else:
    ROOT = Path(__file__).resolve().parent.parent
    RES = ROOT / 'app'
    sys.path.insert(0, str(ROOT / 'tools'))
    DATA = ROOT / 'keymap'
    KEYMAP = DATA / 'keymap.json'
    SINOWISP = ROOT / 'sinowisp.exe'

import config_store  # noqa: E402
import firmware_image  # noqa: E402
import keymap_gen  # noqa: E402

BASE_FW = RES / 'firmware-base.hex'
DEFAULT_KEYMAP = RES / 'default-keymap.json'
NAMES = json.loads((RES / 'keycodes.json').read_text(encoding='utf-8'))
HOST = '127.0.0.1'
PORT = int(os.environ.get('F75J_PORT', '8075'))  # 開発中に別の番号で動かすとき用
VERSION = '0.13.1'

# Windows のコンソールの文字コード（日本語版は cp932）で、外部プログラムの出力を読む
CONSOLE_ENC = 'cp932' if sys.platform == 'win32' else 'utf-8'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)  # 黒い窓を出さない


def dump_keymap(data):
    """keymap.json を、1 行 = キーボードの 1 行 の読みやすい形で書く（プロファイルの形）。"""
    J = lambda v: json.dumps(v, ensure_ascii=False)
    out = ['{', f'  "keyboard": {J(data.get("keyboard", "AULA F75J"))},', '  "profiles": [']
    profs = data['profiles']
    for pi, prof in enumerate(profs):
        out.append('    {')
        out.append(f'      "name": {J(prof["name"])},')
        knob = prof['knob']
        out.append(f'      "knob": {{"base": {J(knob["base"])}, "fn": {J(knob["fn"])}}},')
        out.append('      "layers": [')
        layers = prof['layers']
        for li, layer in enumerate(layers):
            out.append(f'        {{"name": {J(layer["name"])}, "keys": [')
            rows = layer['keys']
            for ri, row in enumerate(rows):
                out.append('          [' + ', '.join(J(k) for k in row) + ']' + (',' if ri < len(rows) - 1 else ''))
            out.append('        ]}' + (',' if li < len(layers) - 1 else ''))
        out.append('      ]')
        out.append('    }' + (',' if pi < len(profs) - 1 else ''))
    out.append('  ],')
    # マクロ: 1 行 = 1 マクロ
    macros = data.get('macros') or []
    out.append(f'  "lighting": {J(data.get("lighting") or keymap_gen.DEFAULT_LIGHTING)},')
    out.append(f'  "tapping_term": {J(data.get("tapping_term", keymap_gen.DEFAULT_TAPPING_TERM))},')
    out.append('  "macros": [')
    for mi, m in enumerate(macros):
        out.append('    ' + J(m) + (',' if mi < len(macros) - 1 else ''))
    out.append('  ]')
    out.append('}')
    return '\n'.join(out) + '\n'


def load_keymap():
    """保存してあるキー配置を読む。古い形なら「プロファイル × ベース・Fn・タップ」の形に直して保存し直す。"""
    if not KEYMAP.exists():
        DATA.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DEFAULT_KEYMAP, KEYMAP)
    data = json.loads(KEYMAP.read_text(encoding='utf-8'))
    try:
        fixed = keymap_gen.normalize(data)
    except ValueError:
        return data  # 直せないときはそのまま見せる（保存のときにエラーで知らせる）
    if fixed != data:
        KEYMAP.write_text(dump_keymap(fixed), encoding='utf-8', newline='\n')
    return fixed


def default_keymap():
    return keymap_gen.normalize(json.loads(DEFAULT_KEYMAP.read_text(encoding='utf-8')))


def run(cmd, timeout):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    text = (r.stdout + r.stderr).decode(CONSOLE_ENC, errors='replace')
    return r.returncode, text


def device_status():
    """キーボードが USB でつながっているか、今どのファームか。"""
    ps = ("Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\\\VID_258A&PID_010C\\\\' } | "
          "ForEach-Object { (Get-PnpDeviceProperty -InstanceId $_.InstanceId "
          "-KeyName 'DEVPKEY_Device_BusReportedDeviceDesc').Data }")
    try:
        _, text = run(['powershell', '-NoProfile', '-Command', ps], 30)
    except Exception as e:  # noqa: BLE001
        return {'connected': False, 'name': '', 'error': str(e)}
    name = text.strip().splitlines()[0] if text.strip() else ''
    return {'connected': bool(name), 'name': name}


SYNC = DATA / 'sync.json'  # キーボードとの同期の記録（最後に書き込んだ / 読み込んだ設定の指紋）


def load_sync():
    try:
        return json.loads(SYNC.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_sync(hash_, when, how):
    DATA.mkdir(parents=True, exist_ok=True)
    SYNC.write_text(json.dumps({'hash': hash_, 'at': when, 'how': how}, ensure_ascii=False), encoding='utf-8')


def sync_state(data):
    """エディタの内容と、キーボード（最後に書き込んだ / 読み込んだもの）との関係。"""
    rec = load_sync()
    try:
        h = config_store.config_hash(keymap_gen.normalize(data))
    except ValueError:
        return {'state': 'invalid'}
    if not rec.get('hash'):
        return {'state': 'unknown'}
    return {'state': 'same' if rec['hash'] == h else 'changed', 'at': rec.get('at'), 'how': rec.get('how')}


def now_text():
    return time.strftime('%Y-%m-%d %H:%M')


def read_keyboard():
    """キーボードからファームを読み出して、保存されている設定ファイルを取り出す。"""
    with tempfile.TemporaryDirectory() as tmp:
        hexpath = Path(tmp) / 'read.hex'
        code, log = run([str(SINOWISP), 'read', '-d', 'aula-f75', str(hexpath)], 300)
        if code != 0 or not hexpath.exists():
            return {'ok': False, 'reason': 'read', 'log': log[-4000:]}
        img = firmware_image.FirmwareImage.load(hexpath)
    doc = img.read_config()
    if doc is None:
        return {'ok': False, 'reason': 'noconfig'}
    data = keymap_gen.normalize(doc['keymap'])
    h = config_store.config_hash(data)
    save_sync(h, doc.get('written_at') or now_text(), 'read')
    return {'ok': True, 'data': data, 'written_at': doc.get('written_at'), 'app_version': doc.get('app_version')}


def file_dialog(save, name=''):
    """ファイルを選ぶ窓（窓のアプリのときだけ）。選ばなかったら None。"""
    import webview
    win = _window[0]
    kind = webview.SAVE_DIALOG if save else webview.OPEN_DIALOG
    types = ('キー配置 (*.json)', 'すべてのファイル (*.*)')
    r = win.create_file_dialog(kind, save_filename=name, file_types=types) if save \
        else win.create_file_dialog(kind, file_types=types)
    if not r:
        return None
    return r if isinstance(r, str) else r[0]


def import_text(text):
    try:
        raw = json.loads(text)
    except ValueError as e:
        return {'ok': False, 'errors': [f'ファイルの中身が JSON ではない: {e}']}
    if isinstance(raw, dict) and raw.get('format') == 'f75j-config':  # キーボードの設定ファイルの形でもよい
        raw = raw.get('keymap')
    try:
        data = keymap_gen.normalize(raw)
        keymap_gen.generate(data, NAMES)
    except ValueError as e:
        return {'ok': False, 'errors': str(e).splitlines()}
    return {'ok': True, 'data': data}


def flash(data):
    """キー配置をファームに差し込んで、キーボードに書き込む。"""
    light_id = secrets.randbelow(0xFFFF) + 1  # 書き込みごとに変える番号（キーボードは、新しい番号のときだけ反映する）
    _, values, enc, (mdir, msteps), light, tt = keymap_gen.generate(data, NAMES, light_id)
    img = firmware_image.FirmwareImage.load(BASE_FW)
    img.write_keymap(keymap_gen.pack(values), keymap_gen.pack_encoder(enc),
                     keymap_gen.pack_macros(mdir, msteps), light, tt)
    norm = keymap_gen.normalize(data)
    when = now_text()
    img.write_config(config_store.pack(norm, when, VERSION))  # 入りきらなければ ValueError
    with tempfile.TemporaryDirectory() as tmp:
        hexpath = Path(tmp) / 'aula-f75j_keymap.hex'
        img.save(hexpath)
        # --force: 「60KB より小さいので 0 で埋める」の確認を省く（毎回出るため）
        code, log = run([str(SINOWISP), 'write', '--force', '-d', 'aula-f75', str(hexpath)], 300)
    if code == 0:
        save_sync(config_store.config_hash(norm), when, 'write')
    return code == 0, log


class Handler(BaseHTTPRequestHandler):
    server_version = 'F75JKeymap/' + VERSION

    def log_message(self, fmt, *args):  # 端末を静かにする
        pass

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        n = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(n).decode('utf-8'))

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            body = (RES / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/favicon.ico':
            body = (RES / 'icon.ico').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'image/x-icon')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/api/keymap':
            self.send_json(load_keymap())
        elif self.path == '/api/default':
            self.send_json(default_keymap())
        elif self.path == '/api/names':
            # 入力の候補用: [キー名, 数値] の一覧（KC_ は外す）。
            # 使えるのは、普通のキー・メディアキーなど（0x00FF まで）と、F75J 独自のキー（SAFE_RANGE 以降）。
            # その間（0x0100〜）は QMK の内部用で、このファームでは意味がないので出さない。
            safe = NAMES.get('FX_NEXT', 0x7E40)
            out = {}
            for n, v in NAMES.items():
                if n.startswith(('QK_', 'RGB_', 'BL_', 'MS_')) or n == '_______' or not (0x0004 <= v <= 0x00FF or v >= safe):
                    continue
                out.setdefault(n[3:] if n.startswith('KC_') else n, v)
            for a, target in keymap_gen.ALIASES.items():
                if target in NAMES:
                    out.setdefault(a, NAMES[target])
            self.send_json(sorted([k, v] for k, v in out.items()))
        elif self.path == '/api/device':
            self.send_json(device_status())
        elif self.path == '/api/ping':
            _last_ping[0] = time.monotonic()
            self.send_json({'ok': True})
        elif self.path == '/api/info':
            self.send_json({'version': VERSION, 'keymap_path': str(KEYMAP)})
        else:
            self.send_error(404)

    def do_POST(self):
        # ほかのサイトから勝手に呼ばれないように、この画面からの呼び出しだけ受ける
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://{HOST}:{PORT}', f'http://localhost:{PORT}'):
            self.send_error(403)
            return

        if self.path in ('/api/save', '/api/flash'):
            data = self.read_json()
            try:
                keymap_gen.generate(data, NAMES)
            except ValueError as e:
                self.send_json({'ok': False, 'errors': str(e).splitlines()})
                return
            DATA.mkdir(parents=True, exist_ok=True)
            KEYMAP.write_text(dump_keymap(keymap_gen.normalize(data)), encoding='utf-8', newline='\n')
            if self.path == '/api/save':
                self.send_json({'ok': True})
                return
            _busy[0] += 1
            try:
                ok, log = flash(data)
            except Exception as e:  # noqa: BLE001
                ok, log = False, f'書き込みの準備でエラー: {e}'
            finally:
                _busy[0] -= 1
                _last_ping[0] = time.monotonic()
            self.send_json({'ok': ok, 'log': log[-6000:]})
        elif self.path == '/api/sync-state':
            self.send_json(sync_state(self.read_json()))
        elif self.path == '/api/read-keyboard':
            _busy[0] += 1
            try:
                self.send_json(read_keyboard())
            except Exception as e:  # noqa: BLE001
                self.send_json({'ok': False, 'reason': 'error', 'log': str(e)})
            finally:
                _busy[0] -= 1
                _last_ping[0] = time.monotonic()
        elif self.path == '/api/export':
            data = self.read_json()
            text = dump_keymap(keymap_gen.normalize(data['data']))
            if _window[0] is None:  # ブラウザで開いているとき: 画面のほうで保存する
                self.send_json({'ok': True, 'fallback': True, 'text': text})
                return
            path = file_dialog(True, data.get('name') or 'F75J の配置.json')
            if not path:
                self.send_json({'ok': False, 'cancelled': True})
                return
            Path(path).write_text(text, encoding='utf-8', newline='\n')
            self.send_json({'ok': True, 'path': str(path)})
        elif self.path == '/api/import':
            if _window[0] is None:
                self.send_json({'ok': False, 'fallback': True})
                return
            path = file_dialog(False)
            if not path:
                self.send_json({'ok': False, 'cancelled': True})
                return
            try:
                text = Path(path).read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError) as e:
                self.send_json({'ok': False, 'errors': [f'ファイルを読めない: {e}']})
                return
            r = import_text(text)
            r['path'] = str(path)
            self.send_json(r)
        elif self.path == '/api/import-text':
            self.send_json(import_text(self.read_json().get('text', '')))
        elif self.path == '/api/bye':
            _bye_at[0] = time.monotonic()
            self.send_json({'ok': True})
        elif self.path == '/api/dirty':
            # 保存していない変更があるときだけ、窓の ✕ で閉じる前に確認を出す
            if _window[0] is not None:
                _window[0].confirm_close = bool(self.read_json().get('dirty'))
            self.send_json({'ok': True})
        elif self.path == '/api/quit':
            self.send_json({'ok': True})
            if _window[0] is not None:  # 窓のアプリなら、窓を閉じる（閉じたらアプリも終わる）
                threading.Thread(target=_window[0].destroy, daemon=True).start()
            else:
                threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_error(404)


_window = [None]  # 窓のアプリのときの窓


def main_native(webview):
    """アプリ専用の窓で開く。窓を閉じたら終わる。番号は空いているものを自動で使う。"""
    global PORT
    srv = ExclusiveServer((HOST, 0), Handler)
    PORT = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _window[0] = webview.create_window(
        f'AULA F75J キー配置エディタ {VERSION}', f'http://{HOST}:{PORT}/',
        width=1240, height=900, min_size=(900, 640),
        # 窓の ✕ で閉じるときの確認の文（保存していない変更があるときだけ出す。/api/dirty）
        localization={'global.quitConfirmation': '保存していない変更があります。閉じますか？'})
    webview.start()  # 窓が閉じられるまで、ここで待つ
    srv.shutdown()


def main():
    if '--browser' not in sys.argv:
        try:
            import webview  # pywebview（Windows では Edge の WebView2 を使う）
        except ImportError:
            webview = None
        if webview is not None:
            main_native(webview)
            return
    main_browser()


def main_browser():
    """ブラウザのタブで開く（開発用、または pywebview がないとき）。"""
    url = f'http://{HOST}:{PORT}'
    try:
        srv = ExclusiveServer((HOST, PORT), Handler)
    except OSError:
        # もう起動している: 画面だけ開く
        webbrowser.open(url)
        return
    if sys.stdout:  # 窓なしの exe では標準出力がない
        print(f'AULA F75J キー配置エディタ {VERSION}: {url}')
    if '--no-browser' not in sys.argv:
        webbrowser.open(url)
    threading.Thread(target=watchdog, args=(srv,), daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


class ExclusiveServer(ThreadingHTTPServer):
    """同じ番号を 2 つのアプリで使えないようにする（Windows の SO_REUSEADDR は二重起動を許してしまう）。"""
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


# アプリを裏で動かし続けないための見張り。
# - 画面を閉じるとき、ページは /api/bye を送る → 数秒待って、新しい画面から /api/ping が
#   来なければ終わる（再読み込みなら、すぐに ping が来るので終わらない）。
# - bye が届かなかったとき（ブラウザごと落ちたなど）の保険として、ping が長く途絶えても終わる。
#   裏のタブはタイマーが 1 分に 1 回まで遅くなるので、こちらは余裕を持たせる。
IDLE_EXIT_SEC = 180
BYE_EXIT_SEC = 4
_last_ping = [time.monotonic()]
_bye_at = [None]
_busy = [0]  # 書き込み中は終わらない


def watchdog(srv):
    while True:
        time.sleep(1)
        if _busy[0]:
            continue
        now = time.monotonic()
        bye = _bye_at[0]
        if (bye is not None and _last_ping[0] < bye and now - bye > BYE_EXIT_SEC) or \
                now - _last_ping[0] > IDLE_EXIT_SEC:
            srv.shutdown()
            return


if __name__ == '__main__':
    main()
