; Setup wizard for Discord Message Cleaner (Inno Setup 6)
; Build with build_installer.bat, or open this file in Inno Setup and press Compile.

#define MyAppName "Discord Message Cleaner"
#define MyAppVersion "7.5.0"
#define MyAppPublisher "08Raph"
#define MyAppExeName "DiscordMessageCleaner.exe"

[Setup]
AppId={{8C95F197-85E3-4FF1-83DE-5BD49E6D7A81}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Installs for the current user, no admin rights needed (user can switch to all users)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
LicenseFile=LICENSE
InfoBeforeFile=installer_info.txt
OutputDir=installer_output
OutputBaseFilename=DiscordMessageCleaner-Setup-{#MyAppVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppName} Setup

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\DiscordMessageCleaner\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; picture and video cache (re-downloaded when needed)
Type: filesandordirs; Name: "{localappdata}\DiscordMessageCleaner"

[UninstallRun]
; stop the background logger and remove the auto-clean task
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM DiscordMessageCleaner.exe"; Flags: runhidden; RunOnceId: "StopApp"
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""DiscordMessageCleaner AutoClean"""; Flags: runhidden; RunOnceId: "RemoveTask"

[Code]
// Ask on uninstall whether to also remove settings and the saved login.
// Backups in Documents\Discord Cleaner Backups are never removed.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usUninstall then
    RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run',
                   'DiscordMessageCleanerLogger');
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\DiscordMessageCleaner');
    if DirExists(DataDir) then
      if MsgBox('Also remove your settings, saved accounts, keep list and saved deleted messages?' + #13#10 +
                '(Your backups in Documents are kept.)', mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
