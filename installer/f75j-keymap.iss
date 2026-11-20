; AULA F75J キー配置エディタ のインストーラー（Inno Setup 6）
; 作り方: tools\package.ps1 を実行する（先に exe を作ってから、これをコンパイルする）

#define AppName "AULA F75J キー配置エディタ"
#define AppVersion "0.14.0"
#define AppExe "F75JKeymap.exe"

[Setup]
AppId={{5B7F0B2E-7A1C-4F4B-9E5D-F75A11F75A01}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=AULA F75J project
DefaultDirName={localappdata}\Programs\AULA F75J Keymap
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; 管理者の権限なしで、自分のユーザーにだけ入れる
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=AULA-F75J-Keymap-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\app\icon.ico

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作る"; GroupDescription: "ショートカット:"

[Files]
Source: "..\dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} をアンインストール"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "今すぐ起動する"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; アンインストールの前に、動いているアプリを終了させる
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "StopApp"

[Code]
// インストールの前に、動いているアプリを終了させる（ファイルが使用中で上書きできないのを防ぐ）
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Sleep(500);
  Result := '';
end;
