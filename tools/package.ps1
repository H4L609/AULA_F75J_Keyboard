# AULA F75J キー配置エディタ を、1 つの exe とインストーラーにまとめる（作る側の PC で実行）。
# 使い方（プロジェクトのフォルダで）:  powershell -ExecutionPolicy Bypass -File tools\package.ps1
# 必要なもの: Python + PyInstaller（pip install pyinstaller）、Inno Setup 6
# できあがり: dist\F75JKeymap.exe と dist\AULA-F75J-Keymap-Setup-<版>.exe

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    foreach ($f in 'app\firmware-base.hex', 'app\keycodes.json', 'app\default-keymap.json', 'sinowisp.exe') {
        if (-not (Test-Path $f)) { throw "$f がありません（先に tools\build-f75j.ps1 を実行してください）" }
    }

    # 1. exe を作る（Python ごと 1 つのファイルにまとめる。黒い窓は出さない）
    #    アイコンは app\icon.ico（tools\make_icon.py で作る）。窓のアイコンも exe のものが使われる
    python -m PyInstaller --noconfirm --clean --onefile --windowed `
        --name F75JKeymap `
        --icon "$root\app\icon.ico" `
        --paths tools `
        --distpath dist --workpath build\pyinstaller --specpath build\pyinstaller `
        --add-data "$root\app\index.html;." `
        --add-data "$root\app\icon.ico;." `
        --add-data "$root\app\default-keymap.json;." `
        --add-data "$root\app\keycodes.json;." `
        --add-data "$root\app\firmware-base.hex;." `
        --add-binary "$root\sinowisp.exe;." `
        app\server.py
    if ($LASTEXITCODE -ne 0) { throw 'exe を作れませんでした' }

    # 2. インストーラーを作る
    $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
              "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) { throw 'Inno Setup 6 が見つかりません' }
    & $iscc /Q installer\f75j-keymap.iss
    if ($LASTEXITCODE -ne 0) { throw 'インストーラーを作れませんでした' }

    Get-ChildItem dist | Format-Table Name, Length -AutoSize
} finally {
    Pop-Location
}
