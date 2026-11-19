# 自作ファームのビルド・書き込み・元に戻す手順

ロードマップ 2 段目の成果物。コマンドは、すべてプロジェクトのフォルダ（`C:\Claude Work Folder\life\AULA F75J`）で実行する。

## 構成

| 場所 | 中身 |
|---|---|
| `third_party/smk_aulaF75/` | 自作ファームのソース（Thaolia/smk_aulaF75）。F75J 用は `src/keyboards/aula-f75j/` |
| `tools/build-f75j.ps1` | ビルド用のスクリプト |
| `tools/hostcc/cc` | Windows でビルドするための補助（`cc` を MSVC の `cl` に読み替える） |
| `firmware/aula-f75j_smk.hex` | できあがったファーム |
| `backup/` | 出荷時ファームのバックアップ（元に戻すときに使う） |

必要な道具: SDCC 4.3 以上（`winget install SDCC.SDCC`）、meson と ninja（`python -m pip install meson ninja`）、Visual Studio の C コンパイラ。

## 1. ビルド

```
powershell -ExecutionPolicy Bypass -File tools\build-f75j.ps1
```

## 2. 書き込み（キーボードをケーブルでつないだ状態で）

```
.\sinowisp.exe write -d aula-f75 firmware\aula-f75j_smk.hex
```

- 「サイズが足りないので 0 で埋める。続けるか？」と聞かれたら `y` と答える。ファームは 60KB より小さいので、毎回聞かれる。
- 起動用の領域（ブートローダ）には書き込まれない。

## 3. 元に戻す（出荷時ファームに戻す）

```
.\sinowisp.exe write -d aula-f75 backup\F75J_firmware.hex
```

自作ファームが動いていて、USB でつながっていれば、この方法で戻せる。

## 4. うまく動かないとき

| 状態 | 対処 |
|---|---|
| USB で認識はされる | 上の「3. 元に戻す」を実行する |
| USB で認識されないが、キーは反応する | **Fn + Esc を 3 秒押し続ける**と、書き込み待ちの状態（ブートローダ）に入る（自作ファームに追加した機能）。そのあとで「3. 元に戻す」を実行する |
| 何をしても反応しない | Arduino Nano を基板に配線して書き戻す（sinodude-serial）。`backup/F75J_full.hex` を使う |

## F75J 用に変えたところ（F75 版との差）

`src/keyboards/aula-f75j/` は `aula-f75/` をコピーして、次の点を変えた。

- 列を 17 にした（`kbdef.h`、`user_matrix.c`）。c16 = P4.6（¥ キー）。c15 は P4.5（接続方式の切り替えスイッチ）なので、**出力にしない空の列**として扱う。
- 日本語配列の配置にした（`layouts/default/layout.c`）。
- ライトの効果に使う表を、F75J の出荷時ファームから取り出した 17 列ぶんに差し替えた（`aula_fx.c`、`aula_fx.h`、`aula_rgb.h`）。
- Bluetooth の名前を「AULA F75 JIS 3.0 / 5.0」に、USB の名前を「AULA F75 JIS SMK」にした。
- 非常口として、`BOOT_HOLD` キー（Fn + Esc を 3 秒押す → ブートローダへ）を足した（`kb.c`、`indicators.c`）。
- `meson.build` に `aula-f75j` を足した。
- ダイヤルを回すたびに全体が脈打つように光る演出（移植版の作者が足したもの。出荷時にはない）を止めた（`aula_encoder.c` の `AULA_ENC_BEAT`）。

## 出荷時との違い（未対応のもの）

- Fn + F3（Alt+Tab）と Fn + F4（Win+E）: SMK は「同時押しを 1 つのキーに割り当てる」ことにまだ対応していないので、空けてある。
- Fn + Win（Win ロック）、Fn + Q/W/E（OS モード）、Fn + B（電池表示）、Fn + G: 自作ファームにはない機能なので、空けてある。

## まだ確かめていないこと

- 2026-11-18: F75J の実機に書き込み、有線で文字が打てることを確認した。日本語配列のキー（¥、ろ、無変換、変換、かな、半角/全角、]）もすべて打てた。ダイヤルの音量操作も動いた。
- 2.4GHz（付属の受信機）でも文字が打てることを確認した。
- 未確認: Bluetooth（ユーザーは使わないので試していない）、非常口（Fn + Esc 長押し）。
