; Ham Radio AI - Inno Setup Script
; Download Inno Setup from https://jrsoftware.org/isdl.php

#define AppName "Ham Radio AI"
#define AppVersion "1.0.0"
#define AppPublisher "HamRadioAI"
#define AppURL "https://github.com/Xyleneuk/hamradio-ai"
#define AppExeName "HamRadioAI.exe"

[Setup]
AppId={{8F3A2B1C-4D5E-6F7A-8B9C-0D1E2F3A4B5C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE.txt
OutputDir=output
OutputBaseFilename=HamRadioAI_Setup_{#AppVersion}
SetupIconFile=..\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start Ham Radio AI when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
; Main application
Source: "..\dist\HamRadioAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Hamlib
Source: "..\hamlib\bin\*"; DestDir: "{app}\hamlib\bin"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; Store install path for updates
Root: HKCU; Subkey: "Software\HamRadioAI"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"

[Code]
// Check for .NET and VC++ redistributables
function InitializeSetup(): Boolean;
begin
  Result := True;
end;