; TestscenarioMaker CLI Windows Installer Script (NSIS)
;
; This script creates a Windows installer for TestscenarioMaker CLI.
; Requires NSIS (Nullsoft Scriptable Install System).

;--------------------------------
; Modern UI
!include "MUI2.nsh"

; Include EnvVarUpdate for safe PATH management
!addincludedir "${__FILEDIR__}"
!include "LogicLib.nsh"   ; Required for ${If} statements
!include "StrFunc.nsh"    ; For ${StrRep} string replacement
!include "EnvVarUpdate.nsh"

; Define PATH entry as single source of truth
!define PATH_ENTRY "$INSTDIR"  ; The directory to add to PATH

;--------------------------------
; Settings
Name "TestscenarioMaker CLI"
OutFile "TestscenarioMaker-CLI-Setup.exe"
Unicode True

; Default installation directory (no trailing backslash)
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
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
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

  ; Ensure 64-bit registry view on x64
  SetRegView 64

  ; Set output path
  SetOutPath $INSTDIR

  ; Executable file
  File "..\dist\ts-cli.exe"

  ; PowerShell script for URL handling (production)
  File "url_handler.ps1"

  ; Configuration file
  SetOutPath "$INSTDIR\config"
  File "..\config\config.ini"

  ; Write installation info to registry
  WriteRegStr HKLM "SOFTWARE\TestscenarioMaker\CLI" "Install_Dir" "$INSTDIR"

  ; Uninstall information
  WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TestscenarioMaker CLI" "DisplayName"     "TestscenarioMaker CLI"
  WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TestscenarioMaker CLI" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TestscenarioMaker CLI" "NoModify"        1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TestscenarioMaker CLI" "NoRepair"        1
  WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TestscenarioMaker CLI" "Publisher"       "TestscenarioMaker Team"
  WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TestscenarioMaker CLI" "DisplayVersion"  "1.0.0"

  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Add to PATH" SEC02
  ; Normalize backslashes before adding to PATH (prevent double backslash)
  StrCpy $R0 "${PATH_ENTRY}"
  ${StrRep} $R0 $R0 "\\\\" "\\"  ; Collapse \\\\ to \\.

  ; Append to system PATH using EnvVarUpdate (handles duplicates automatically)
  ${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$R0"
  DetailPrint "EnvVarUpdate(Add PATH@HKLM): $0"

  ; Check for errors
  ${If} $0 == "error"
    DetailPrint "Warning: Could not update PATH variable"
  ${Else}
    DetailPrint "Successfully added $R0 to system PATH"
  ${EndIf}

  ; Broadcast environment change so new consoles/processes can see updated PATH
  System::Call 'USER32::SendMessageTimeout(p 0xffff, i 0x1A, p 0, t "Environment", i 2, i 5000, *p .r0)'
SectionEnd

Section "Desktop Shortcut" SEC03
  ; Create desktop shortcut
  CreateShortcut "$DESKTOP\TestscenarioMaker CLI.lnk" "$INSTDIR\ts-cli.exe" "" "$INSTDIR\ts-cli.exe" 0
SectionEnd

Section "Start Menu Shortcut" SEC04
  ; Create start menu folder
  CreateDirectory "$SMPROGRAMS\TestscenarioMaker"

  ; Create start menu shortcuts
  CreateShortcut "$SMPROGRAMS\TestscenarioMaker\TestscenarioMaker CLI.lnk" "$INSTDIR\ts-cli.exe" "" "$INSTDIR\ts-cli.exe" 0
  CreateShortcut "$SMPROGRAMS\TestscenarioMaker\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
SectionEnd

Section "Register URL Protocol" SEC05
  ; Settings for 32/64-bit compatibility
  SetShellVarContext all

  ; Register testscenariomaker:// protocol
  WriteRegStr HKCR "testscenariomaker" "" "URL:TestscenarioMaker Protocol"
  WriteRegStr HKCR "testscenariomaker" "URL Protocol" ""

  ; Set the icon for the protocol (using single backslashes to prevent double escaping)
  WriteRegStr HKCR "testscenariomaker\DefaultIcon" "" "$INSTDIR\ts-cli.exe,1"

  ; Create the command key structure
  WriteRegStr HKCR "testscenariomaker\shell" "" ""
  WriteRegStr HKCR "testscenariomaker\shell\open" "" ""

  ; Register command for PRODUCTION - PowerShell with visible console for debugging
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
  ; Use 64-bit registry view for consistency
  SetRegView 64

  ; ===== PATH REMOVAL FIRST (before deleting our registry keys) =====

  ; Prepare canonical token from actual Install_Dir in registry
  ReadRegStr $R0 HKLM "SOFTWARE\TestscenarioMaker\CLI" "Install_Dir"
  ${If} $R0 == ""
    ; Fallback to macro if registry key is missing
    StrCpy $R0 "${PATH_ENTRY}"
  ${EndIf}

  ; Normalize backslashes (\\ -> \) to match the canonical PATH entry
  ${un.StrRep} $R0 $R0 "\\\\" "\\"

  ; Optional: strip trailing backslash if any (defensive)
  StrLen $R1 $R0
  ${If} $R1 > 0
    StrCpy $R2 $R0 1 -1
    ${If} $R2 == "\\"
      IntOp $R1 $R1 - 1
      StrCpy $R0 $R0 $R1
    ${EndIf}
  ${EndIf}

  ; Remove canonical form from both HKLM and HKCU
  ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$R0"
  DetailPrint "EnvVarUpdate(Remove PATH@HKLM, canonical): $0"
  ${un.EnvVarUpdate} $1 "PATH" "R" "HKCU" "$R0"
  DetailPrint "EnvVarUpdate(Remove PATH@HKCU, canonical): $1"

  ; Create and remove historical double-backslash token (legacy cleanup)
  ${un.StrRep} $R3 $R0 "\\" "\\\\"
  ${un.EnvVarUpdate} $2 "PATH" "R" "HKLM" "$R3"
  DetailPrint "EnvVarUpdate(Remove PATH@HKLM, double-backslash): $2"
  ${un.EnvVarUpdate} $3 "PATH" "R" "HKCU" "$R3"
  DetailPrint "EnvVarUpdate(Remove PATH@HKCU, double-backslash): $3"

  ; Broadcast environment change so removal reflects in new processes
  System::Call 'USER32::SendMessageTimeout(p 0xffff, i 0x1A, p 0, t "Environment", i 2, i 5000, *p .r0)'

  ; ================== FILES / SHORTCUTS / REGISTRY CLEANUP ==================

  ; Delete files
  Delete "$INSTDIR\ts-cli.exe"
  Delete "$INSTDIR\config\config.ini"
  Delete "$INSTDIR\uninstall.exe"

  ; Delete directories
  RMDir "$INSTDIR\config"
  RMDir "$INSTDIR"

  ; Delete shortcuts
  Delete "$DESKTOP\TestscenarioMaker CLI.lnk"
  Delete "$SMPROGRAMS\TestscenarioMaker\TestscenarioMaker CLI.lnk"
  Delete "$SMPROGRAMS\TestscenarioMaker\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\TestscenarioMaker"

  ; Clean registry (do this AFTER PATH removal)
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TestscenarioMaker CLI"
  DeleteRegKey HKLM "SOFTWARE\TestscenarioMaker\CLI"
  DeleteRegKey HKLM "SOFTWARE\TestscenarioMaker"

  ; Remove URL protocol
  DeleteRegKey HKCR "testscenariomaker"
SectionEnd

;--------------------------------
; Functions

; Installation initialization
Function .onInit
  Call Is64Bit
  Pop $0
  StrCmp $0 "1" 0 Not64
    SetRegView 64
    StrCpy $INSTDIR "$PROGRAMFILES64\TestscenarioMaker CLI"
    Goto EndIf
  Not64:
    StrCpy $INSTDIR "$PROGRAMFILES32\TestscenarioMaker CLI"
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
