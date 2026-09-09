; Script do Inno Setup para o instalador do Recorte.ai.
;
; Como gerar o instalador:
;   1. Instale o Inno Setup (gratuito): https://jrsoftware.org/isdl.php
;   2. Gere o executável antes, se ainda não gerou: pyinstaller app_gui.spec
;   3. Abra este arquivo no Inno Setup Compiler e clique em "Compile"
;      -- ou pela linha de comando:
;         "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;   4. O instalador fica em Output\Recorte.ai-Setup-1.0.0.exe
;
; Atualizar a versão: troque o valor de MyAppVersion abaixo para bater com
; APP_VERSION em config.py.

#define MyAppName "Recorte.ai"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Recorte.ai"
#define MyAppExeName "app_gui.exe"

[Setup]
; Identificador fixo do app -- não mude entre versões, é o que permite ao
; instalador detectar e atualizar uma instalação existente em vez de duplicar.
AppId={{522FC393-1E3D-4553-A1AC-975868E4DCCF}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
DisableProgramGroupPage=yes
; "lowest" instala só para o usuário atual, sem precisar de permissão de
; administrador nem prompt do UAC -- adequado para um utilitário simples.
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; O app_gui.exe já é um executável "onefile" -- ícone e outros recursos vão
; embutidos nele pelo PyInstaller, então não há mais nada para copiar.
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove as preferências salvas (idioma, largura da barra lateral) ao
; desinstalar -- são só configurações triviais, sem perda real para o usuário.
Type: filesandordirs; Name: "{userappdata}\RecorteAI"
