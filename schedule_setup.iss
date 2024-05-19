[setup]
AppName=Schedule
AppVersion=1.0.0
DefaultDirName={pf}\Schedule
OutputBaseFilename="setup"
;PrivilegesRequired=lowest

[Files]
Source: "dist/Schedule.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist/schedule_console.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist/nvdaControllerClient64.dll"; DestDir: "{app}"
Source: "dist/SAAPI64.dll"; DestDir: "{app}"
Source: "readme.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme
; news must always be news.txt inside the installer, but the actual file can be news.txt or news.old.txt
Source: "{code:GetNewsFile}"; DestDir: "{app}"; Flags: ignoreversion external; DestName: "news.txt"

[Code]
function GetNewsFile(Param: String): String;
begin
    Result := 'news.txt';
    if not FileExists(Result) then
        Result := 'news.old.txt';
end;

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
Filename: "{app}\Schedule.exe"; Description: "{cm:LaunchProgram,Schedule}"; Flags: nowait postinstall
