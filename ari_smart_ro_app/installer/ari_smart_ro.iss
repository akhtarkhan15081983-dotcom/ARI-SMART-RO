; ARI SMART RO Windows Installer
; Version/build are injected by CI. Defaults support local developer builds.

#define MyAppName "ARI SMART RO"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#ifndef MyAppBuild
  #define MyAppBuild "1"
#endif
#define MyAppPublisher "ARI SMART RO"
#define MyAppExeName "ARI_SMART_RO.exe"

[Setup]
AppId={{B2B18C7D-0BA8-4F73-8E7C-5F0EB7A82E5E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ARI SMART RO
DefaultGroupName=ARI SMART RO
DisableProgramGroupPage=yes
OutputDir=..\build\windows\installer
OutputBaseFilename=ARI-SMART-RO-Setup-v{#MyAppVersion}
SetupIconFile=..\windows\runner\resources\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#MyAppVersion}.{#MyAppBuild}
VersionInfoCompany=ARI SMART RO
VersionInfoDescription=ARI SMART RO Windows Installer
VersionInfoProductName=ARI SMART RO
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) 2026 ARI SMART RO. All rights reserved.
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\build\windows\x64\runner\Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ARI SMART RO"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ARI SMART RO"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch ARI SMART RO"; Flags: nowait postinstall skipifsilent
