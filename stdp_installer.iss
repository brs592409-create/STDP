; ============================================================
; STDP Installer — Inno Setup Script
; ============================================================
; Bu script, PyInstaller ile oluşturulan STDP çıktısını ve
; st-setup-1.8.30.exe dosyasını tek bir Windows installer'a
; paketler.
;
; Derleme: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" stdp_installer.iss
; ============================================================

#define MyAppName "STDP"
#define MyAppFullName "STDP - Steam Tool Depotbox Pipeline"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "STDP"
#define MyAppExeName "STDP.exe"

[Setup]
AppId={{A3F7B2C1-9D4E-4F6A-8B2C-1E3D5F7A9B0C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppFullName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=STDP_Setup
Compression=lzma2/ultra64
SolidCompression=yes
LZMAAlgorithm=1
LZMANumBlockThreads=6
LZMADictionarySize=65536
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppFullName}
MinVersion=10.0

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; STDP uygulama dosyaları (PyInstaller dist/STDP/ klasörü)
Source: "dist\STDP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; SteamTools kurulum dosyası — geçici dizine kopyalanır ve kurulum sonrası silinir
Source: "bundled_installers\st-setup-1.8.30.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall

[Icons]
Name: "{group}\{#MyAppFullName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; st-setup-1.8.30.exe sessiz kurulumu (NSIS /S flag)
Filename: "{tmp}\st-setup-1.8.30.exe"; Parameters: "/S"; StatusMsg: "SteamTools kilit motoru kuruluyor..."; Flags: waituntilterminated runhidden

; Kurulum sonrası STDP'yi başlat (isteğe bağlı)
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppFullName} uygulamasını başlat"; Flags: nowait postinstall skipifsilent

[Dirs]
Name: "{localappdata}\{#MyAppName}"
Name: "{localappdata}\{#MyAppName}\logs"

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"

