[setup]
AppName=Schedule
AppVersion=1.0.0
DefaultDirName={drive:\}\schedule
OutputBaseFilename="setup"

[files]
Source: "dist/Schedule.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist/schedule_console.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist/nvdaControllerClient64.dll"; DestDir: "{app}"
Source: "dist/SAAPI64.dll"; DestDir: "{app}"
Source: "news.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "readme.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Tasks]
Name: desktopicon; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Icons]
; define the icons for schedule gui and console client
Name: "{group}\Schedule"; Filename: "{app}\Schedule.exe"; WorkingDir: "{app}"; HotKey: "CTRL+ALT+S"
Name: "{group}\Schedule Console"; Filename: "{app}\schedule_console.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall Schedule"; Filename: "{uninstallexe}"; WorkingDir: "{app}"
Name: "{commondesktop}\Schedule"; Filename: "{app}\Schedule.exe"; WorkingDir: "{app}"; Tasks: desktopicon


[languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[run]
Filename: "{app}\Schedule.exe"; Description: "{cm:LaunchProgram,Schedule}"; Flags: nowait postinstall skipifsilent
