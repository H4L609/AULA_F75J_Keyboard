# AULA F75J キー配置エディタ

AULA F75J（日本語配列・3 モード）のすべてのキーを、自由に割り当てられるようにするプロジェクトです。
出荷時のファームでは変えられない Fn 層も含めて、キー・ノブ・マクロ・ライトを、Windows のアプリから設定できます。

<img src="app/icon-256.png" width="96" alt="アイコン">

> [!WARNING]
> キーボードのファームウェアを書き換えます。自己責任で使ってください。
> 書き換えに失敗しても、ISP ブートローダー（0xF000〜）は消さないので、もう一度書き込めます。

## できること

- すべてのキーの割り当て（ベース層・Fn 層・タップ層の 3 層）。タップと長押しの使い分け
- 右上のノブ（左回し・押す・右回し）の割り当て
- プロファイル 4 つ（キーで切り替え）、マクロ 16 個、マウス操作
- ライトの設定（光り方・明るさ・速さ・色・向き）
- 設定をキーボードの中にも保存し、あとから読み出す。ファイルへの書き出し・読み込み

## 使い方

1. Releases から `AULA-F75J-Keymap-Setup-<版>.exe` を入れる（Python などの準備は要らない）。
2. 「AULA F75J キー配置エディタ」を起動し、キーを選んで割り当てを変える。
3. キーボードを USB ケーブルでつなぎ、右下の「キーボードに反映する」を押す。

くわしくは [docs/app-guide.md](docs/app-guide.md) を見てください。

## フォルダ

| 場所 | 中身 |
|---|---|
| `app/` | アプリ本体（`server.py` と画面の `index.html`）、同梱のファーム、アイコン |
| `docs/` | ファームの解析資料、キー配置の表、説明書、[ロードマップ](docs/roadmap.md) |
| `tools/` | ファームのビルド、キー表の生成、配布物づくりのスクリプト |
| `installer/` | インストーラー（Inno Setup 6）の設定 |
| `firmware/` | ビルドした自作ファーム |
| `keymap/` | 開発用のキー配置ファイル |
| `third_party/smk_aulaF75` | ファームのソース（[SMK の AULA F75 版](https://github.com/Thaolia/smk_aulaF75) に F75J 対応を足したもの）。サブモジュールで、中身は [H4L609/smk_aula_f75j](https://github.com/H4L609/smk_aula_f75j/tree/aula-f75j) の `aula-f75j` ブランチ |

## 作る側の準備

- ファームのビルド: SDCC 4.5、meson、ninja。手順は [docs/flash-guide.md](docs/flash-guide.md)
- 配布物づくり: PyInstaller、pywebview、Inno Setup 6。手順は [docs/app-guide.md](docs/app-guide.md)
- 書き込みツール [sinowisp](https://github.com/carlossless/sinowealth-kb-tool) の `sinowisp.exe` を、このフォルダの直下に置く（リポジトリには入れていない）

サブモジュールごと取ってくるには:

```
git clone --recurse-submodules https://github.com/H4L609/AULA_F75J_Keyboard.git
```

## ライセンス

GPL-2.0（[LICENSE](LICENSE)）。ファームの元になった SMK が GPL-2.0 のためです。
同梱する sinowisp は MIT ライセンスです（[app/licenses](app/licenses)）。

AULA は、このプロジェクトとは関係ありません。
