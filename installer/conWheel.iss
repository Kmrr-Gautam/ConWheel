#define AppName "conWheel"
#define AppVersion "1.0.0"
[Setup]
AppId={{B7C1D3A4-5E2F-4B8A-9C61-0D7E4F2A91B3}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=conWheel
DefaultDirName={autopf}\conWheel
DefaultGroupName=conWheel
OutputBaseFilename=conWheel-Setup
OutputDir=Output
SetupIconFile=..\app\resources\icons\conWheel.ico
UninstallDisplayIcon={app}\conWheel.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern
[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked
Name: "ctxmenu"; Description: "Add ""Convert with conWheel"" to the Explorer right-click menu"; Flags: unchecked
Name: "startup"; Description: "Start conWheel in the tray when I sign in"; Flags: unchecked
[Files]
Source: "..\dist\conWheel\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\conWheel"; Filename: "{app}\conWheel.exe"
Name: "{group}\Uninstall conWheel"; Filename: "{uninstallexe}"
Name: "{autodesktop}\conWheel"; Filename: "{app}\conWheel.exe"; Tasks: desktopicon
[Registry]
Root: HKCU; Subkey: "Software\Classes\*\shell\conWheel"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Convert with conWheel"; Tasks: ctxmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\conWheel"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\conWheel.exe"; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\conWheel\command"; ValueType: string; ValueData: """{app}\conWheel.exe"" --convert ""%1"""; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "conWheel"; ValueData: """{app}\conWheel.exe"" --tray"; Tasks: startup; Flags: uninsdeletevalue
[Run]
Filename: "{app}\conWheel.exe"; Description: "Launch conWheel"; Flags: nowait postinstall skipifsilent
