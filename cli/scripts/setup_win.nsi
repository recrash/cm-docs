; TestscenarioMaker CLI Windows Installer Script (NSIS)
; 
; This script creates a Windows installer for TestscenarioMaker CLI.
; Requires NSIS (Nullsoft Scriptable Install System).

;--------------------------------
; Modern UI
!include "MUI2.nsh"

;--------------------------------
; Settings
Name "TestscenarioMaker CLI"
OutFile "TestscenarioMaker-CLI-Setup.exe"
Unicode True

; Default installation directory
InstallDir "$PROGRAMFILES64\TestscenarioMaker CLI"

; Registry key for installation path
InstallDirRegKey HKLM "Software\TestscenarioMaker\CLI" "Install_Dir"

; Request admin privileges
RequestExecutionLevel admin

; Compression settings
SetCompressor /SOLID lzma

;--------------------------------
; Interface Settings

; Icon settings (if icon file exists)
; Icon "icon.ico"

; Install pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstall pages
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Language
!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Version Information
VIProductVersion "1.0.0.0"
VIAddVersionKey /LANG=1033 "ProductName" "TestscenarioMaker CLI"
VIAddVersionKey /LANG=1033 "Comments" "CLI tool for local repository analysis"
VIAddVersionKey /LANG=1033 "CompanyName" "TestscenarioMaker Team"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Copyright © 2023 TestscenarioMaker Team"
VIAddVersionKey /LANG=1033 "FileDescription" "TestscenarioMaker CLI Setup"
VIAddVersionKey /LANG=1033 "FileVersion" "1.0.0.0"
VIAddVersionKey /LANG=1033 "ProductVersion" "1.0.0.0"
VIAddVersionKey /LANG=1033 "InternalName" "TestscenarioMaker-CLI-Setup"

;--------------------------------
; Install Sections

Section "Core Files" SEC01
  SectionIn RO
  
  ; Set output path
  SetOutPath $INSTDIR
  
  ; Executable file
  File "..\\dist\\ts-cli.exe"

  ; PowerShell script for URL handling (production)
  File "url_handler.ps1"

  ; Configuration file
  SetOutPath $INSTDIR\\config
  File "..\\config\\config.ini"
  
  ; Write installation info to registry
  WriteRegStr HKLM "SOFTWARE\\TestscenarioMaker\\CLI" "Install_Dir" "$INSTDIR"
  
  ; Uninstall information
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "DisplayName" "TestscenarioMaker CLI"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "UninstallString" '"$INSTDIR\\uninstall.exe"'
  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "NoModify" 1
  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "NoRepair" 1
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "Publisher" "TestscenarioMaker Team"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "DisplayVersion" "1.0.0"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\\uninstall.exe"
  
SectionEnd

Section "Add to PATH" SEC02
  
  ; Add installation directory to system PATH using standard NSIS commands
  ReadRegStr $R0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH"
  StrCpy $R1 "$R0;$INSTDIR"
  WriteRegStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH" $R1
  
SectionEnd

Section "Desktop Shortcut" SEC03
  
  ; Create desktop shortcut
  CreateShortcut "$DESKTOP\\TestscenarioMaker CLI.lnk" "$INSTDIR\\ts-cli.exe" "" "$INSTDIR\\ts-cli.exe" 0
  
SectionEnd

Section "Start Menu Shortcut" SEC04
  
  ; Create start menu folder
  CreateDirectory "$SMPROGRAMS\\TestscenarioMaker"
  
  ; Create start menu shortcuts
  CreateShortcut "$SMPROGRAMS\\TestscenarioMaker\\TestscenarioMaker CLI.lnk" "$INSTDIR\\ts-cli.exe" "" "$INSTDIR\\ts-cli.exe" 0
  CreateShortcut "$SMPROGRAMS\\TestscenarioMaker\\Uninstall.lnk" "$INSTDIR\\uninstall.exe" "" "$INSTDIR\\uninstall.exe" 0
  
SectionEnd

Section "Register URL Protocol" SEC05
  
  ; Settings for 32/64-bit compatibility
  SetShellVarContext all
  
  ; Register testscenariomaker:// protocol
  ; This command creates the key and sets its default value.
  WriteRegStr HKCR "testscenariomaker" "" "URL:TestscenarioMaker Protocol"
  WriteRegStr HKCR "testscenariomaker" "URL Protocol" ""
  
  ; Set the icon for the protocol (using single backslashes to prevent double escaping)
  WriteRegStr HKCR "testscenariomaker\DefaultIcon" "" "$INSTDIR\ts-cli.exe,1"
  
  ; Create the command key structure
  WriteRegStr HKCR "testscenariomaker\shell" "" ""
  WriteRegStr HKCR "testscenariomaker\shell\open" "" ""
  
  ; Register command for PRODUCTION - PowerShell with visible console for debugging
  ; Execute PowerShell script with visible console window for debugging
  ; URL parameters are properly quoted to handle & characters
  WriteRegStr HKCR "testscenariomaker\shell\open\command" "" 'powershell.exe -ExecutionPolicy Bypass -File "$INSTDIR\url_handler.ps1" -url "%1" -exePath "$INSTDIR\ts-cli.exe"'
  
SectionEnd

;--------------------------------
; Section Descriptions

; Language strings
LangString DESC_SEC01 ${LANG_ENGLISH} "TestscenarioMaker CLI core executable and configuration files"
LangString DESC_SEC02 ${LANG_ENGLISH} "Add CLI tool path to system PATH environment variable"
LangString DESC_SEC03 ${LANG_ENGLISH} "Create desktop shortcut"
LangString DESC_SEC04 ${LANG_ENGLISH} "Create start menu shortcuts"
LangString DESC_SEC05 ${LANG_ENGLISH} "Register testscenariomaker:// URL protocol"

; Section description assignments
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
!insertmacro MUI_DESCRIPTION_TEXT ${SEC01} $(DESC_SEC01)
!insertmacro MUI_DESCRIPTION_TEXT ${SEC02} $(DESC_SEC02)
!insertmacro MUI_DESCRIPTION_TEXT ${SEC03} $(DESC_SEC03)
!insertmacro MUI_DESCRIPTION_TEXT ${SEC04} $(DESC_SEC04)
!insertmacro MUI_DESCRIPTION_TEXT ${SEC05} $(DESC_SEC05)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; Uninstall Section

Section "Uninstall"
  
  ; Delete files
  Delete $INSTDIR\\ts-cli.exe
  Delete $INSTDIR\\config\\config.ini
  Delete $INSTDIR\\uninstall.exe
  
  ; Delete directories
  RMDir $INSTDIR\\config
  RMDir $INSTDIR
  
  ; Delete shortcuts
  Delete "$DESKTOP\\TestscenarioMaker CLI.lnk"
  Delete "$SMPROGRAMS\\TestscenarioMaker\\TestscenarioMaker CLI.lnk"
  Delete "$SMPROGRAMS\\TestscenarioMaker\\Uninstall.lnk"
  RMDir "$SMPROGRAMS\\TestscenarioMaker"
  
  ; Clean registry
  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI"
  DeleteRegKey HKLM "SOFTWARE\\TestscenarioMaker\\CLI"
  DeleteRegKey HKLM "SOFTWARE\\TestscenarioMaker"
  
  ; Remove URL protocol
  DeleteRegKey HKCR "testscenariomaker"
  
  ; Remove from PATH using standard NSIS commands
  ReadRegStr $R0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH"
  ; Note: Simple PATH removal - may leave empty entries but won't cause errors
  WriteRegStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH" $R0
  
SectionEnd

;--------------------------------
; Functions

; Installation initialization
Function .onInit
  Call Is64Bit
  Pop $0
  StrCmp $0 "1" 0 Not64
    SetRegView 64
    StrCpy $INSTDIR "$PROGRAMFILES64\\TestscenarioMaker CLI"
    Goto EndIf
  Not64:
    StrCpy $INSTDIR "$PROGRAMFILES32\\TestscenarioMaker CLI"
  EndIf:
FunctionEnd

; Uninstall initialization
Function un.onInit
  Call un.Is64Bit
  Pop $0
  StrCmp $0 "1" 0 Not64u
    SetRegView 64
    Goto EndIfu
  Not64u:
    ; do nothing
  EndIfu:
FunctionEnd

; 64bit detection helper (install)
Function Is64Bit
  System::Call "kernel32::GetCurrentProcess() i .r1"
  System::Call "kernel32::IsWow64Process(i r1, *i .r2)"
  IntCmp $2 0 0 is32 is64
  is64:
    Push 1
    Return
  is32:
    Push 0
    Return
FunctionEnd

; 64bit detection helper (uninstall)
Function un.Is64Bit
  System::Call "kernel32::GetCurrentProcess() i .r1"
  System::Call "kernel32::IsWow64Process(i r1, *i .r2)"
  IntCmp $2 0 0 is32u is64u
  is64u:
    Push 1
    Return
  is32u:
    Push 0
    Return
FunctionEnd