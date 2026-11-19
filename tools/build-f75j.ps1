# AULA F75J 用の自作ファーム（SMK）をビルドする。
# 使い方（プロジェクトのフォルダで）:  powershell -ExecutionPolicy Bypass -File tools\build-f75j.ps1
# できあがったファームは firmware\aula-f75j_smk.hex に置かれる。
# キーボードへの書き込みはしない（書き込みは README の手順で、自分で行う）。

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$src  = Join-Path $root 'third_party\smk_aulaF75'

# SDCC は PATH に入らないことがあるので、ここで足す。
# sinowisp（プロジェクト直下）と、Windows 用の cc の代わり（tools\hostcc）も足す。
$env:Path = "C:\Program Files\SDCC\bin;$root;$root\tools\hostcc;$env:Path"

# キー配置ファイル（keymap\keymap.json）からキー表を作る。まちがいがあればここで止める。
python (Join-Path $root 'tools\keymap_gen.py')
if ($LASTEXITCODE -ne 0) { throw 'keymap.json を直してから、もう一度実行してください' }

Push-Location $src
try {
    if (-not (Test-Path 'build\build.ninja')) {
        meson setup build
    }
    # 日本語版 Windows の文字コードで、ビルド中のチェックの表示が落ちないようにする
    $env:PYTHONUTF8 = '1'
    meson compile -C build aula-f75j_default_smk.hex
    $code = $LASTEXITCODE
    Remove-Item Env:PYTHONUTF8
    if ($code -ne 0) { throw 'ビルドに失敗しました（上のエラーを見てください）' }
} finally {
    Pop-Location
}

# キー表が決まった場所にあり、ほかのコードと重なっていないかを確かめる
python (Join-Path $root 'tools\check_layout.py')
if ($LASTEXITCODE -ne 0) { throw 'ファームのチェックで問題が見つかりました' }

$out = Join-Path $root 'firmware'
New-Item -ItemType Directory -Force $out | Out-Null
Copy-Item (Join-Path $src 'build\aula-f75j_default_smk.hex') (Join-Path $out 'aula-f75j_smk.hex') -Force

# キー配置エディタ（app）に同梱するもの: 元になるファームと、キー名 → 数値の表
Copy-Item (Join-Path $src 'build\aula-f75j_default_smk.hex') (Join-Path $root 'app\firmware-base.hex') -Force
python (Join-Path $root 'tools\keymap_gen.py') --export-names
Write-Host "できあがり: $out\aula-f75j_smk.hex"
