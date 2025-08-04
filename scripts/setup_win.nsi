; TestscenarioMaker CLI Windows 설치 스크립트 (NSIS)
; 
; 이 스크립트는 Windows용 설치 프로그램을 생성합니다.
; NSIS (Nullsoft Scriptable Install System)가 필요합니다.

;--------------------------------
; 현대적인 UI 사용
!include "MUI2.nsh"

;--------------------------------
; 설정
Name "TestscenarioMaker CLI"
OutFile "TestscenarioMaker-CLI-Setup.exe"
Unicode True

; 기본 설치 디렉토리
InstallDir "$PROGRAMFILES64\TestscenarioMaker CLI"

; 레지스트리에서 설치 경로 가져오기
InstallDirRegKey HKLM "Software\TestscenarioMaker\CLI" "Install_Dir"

; 관리자 권한 요청
RequestExecutionLevel admin

; 압축 설정
SetCompressor /SOLID lzma

;--------------------------------
; 인터페이스 설정

; 아이콘 설정 (아이콘 파일이 있는 경우)
; Icon "icon.ico"

; 설치 페이지
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 제거 페이지
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; 언어
!insertmacro MUI_LANGUAGE "Korean"
!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; 버전 정보
VIProductVersion "1.0.0.0"
VIAddVersionKey /LANG=1042 "ProductName" "TestscenarioMaker CLI"
VIAddVersionKey /LANG=1042 "Comments" "로컬 저장소 분석을 위한 CLI 도구"
VIAddVersionKey /LANG=1042 "CompanyName" "TestscenarioMaker Team"
VIAddVersionKey /LANG=1042 "LegalCopyright" "Copyright © 2023 TestscenarioMaker Team"
VIAddVersionKey /LANG=1042 "FileDescription" "TestscenarioMaker CLI 설치 프로그램"
VIAddVersionKey /LANG=1042 "FileVersion" "1.0.0.0"
VIAddVersionKey /LANG=1042 "ProductVersion" "1.0.0.0"
VIAddVersionKey /LANG=1042 "InternalName" "TestscenarioMaker-CLI-Setup"

;--------------------------------
; 설치 섹션

Section "핵심 파일" SEC01
  SectionIn RO
  
  ; 출력 경로 설정
  SetOutPath $INSTDIR
  
  ; 실행 파일
  File "..\\dist\\ts-cli.exe"
  
  ; 설정 파일
  SetOutPath $INSTDIR\\config
  File "..\\config\\config.ini"
  
  ; 레지스트리에 설치 정보 저장
  WriteRegStr HKLM "SOFTWARE\\TestscenarioMaker\\CLI" "Install_Dir" "$INSTDIR"
  
  ; 제거 프로그램 정보
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "DisplayName" "TestscenarioMaker CLI"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "UninstallString" '"$INSTDIR\\uninstall.exe"'
  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "NoModify" 1
  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "NoRepair" 1
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "Publisher" "TestscenarioMaker Team"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI" "DisplayVersion" "1.0.0"
  
  ; 제거 프로그램 생성
  WriteUninstaller "$INSTDIR\\uninstall.exe"
  
SectionEnd

Section "PATH 환경변수 추가" SEC02
  
  ; 시스템 PATH에 설치 디렉토리 추가
  ${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$INSTDIR"
  
SectionEnd

Section "바탕화면 바로가기" SEC03
  
  ; 바탕화면에 바로가기 생성
  CreateShortcut "$DESKTOP\\TestscenarioMaker CLI.lnk" "$INSTDIR\\ts-cli.exe" "" "$INSTDIR\\ts-cli.exe" 0
  
SectionEnd

Section "시작 메뉴 바로가기" SEC04
  
  ; 시작 메뉴 폴더 생성
  CreateDirectory "$SMPROGRAMS\\TestscenarioMaker"
  
  ; 시작 메뉴 바로가기 생성
  CreateShortcut "$SMPROGRAMS\\TestscenarioMaker\\TestscenarioMaker CLI.lnk" "$INSTDIR\\ts-cli.exe" "" "$INSTDIR\\ts-cli.exe" 0
  CreateShortcut "$SMPROGRAMS\\TestscenarioMaker\\제거.lnk" "$INSTDIR\\uninstall.exe" "" "$INSTDIR\\uninstall.exe" 0
  
SectionEnd

Section "URL 프로토콜 등록" SEC05
  
  ; testscenariomaker:// 프로토콜 등록
  WriteRegStr HKCR "testscenariomaker" "" "URL:TestscenarioMaker Protocol"
  WriteRegStr HKCR "testscenariomaker" "URL Protocol" ""
  WriteRegStr HKCR "testscenariomaker\\DefaultIcon" "" "$INSTDIR\\ts-cli.exe,1"
  WriteRegStr HKCR "testscenariomaker\\shell" "" ""
  WriteRegStr HKCR "testscenariomaker\\shell\\open" "" ""
  WriteRegStr HKCR "testscenariomaker\\shell\\open\\command" "" '"$INSTDIR\\ts-cli.exe" analyze --path "%1"'
  
SectionEnd

;--------------------------------
; 섹션 설명

; 언어 문자열
LangString DESC_SEC01 ${LANG_KOREAN} "TestscenarioMaker CLI 핵심 실행 파일과 설정 파일"
LangString DESC_SEC02 ${LANG_KOREAN} "시스템 PATH 환경변수에 CLI 도구 경로를 추가합니다"
LangString DESC_SEC03 ${LANG_KOREAN} "바탕화면에 바로가기를 생성합니다"
LangString DESC_SEC04 ${LANG_KOREAN} "시작 메뉴에 바로가기를 생성합니다"
LangString DESC_SEC05 ${LANG_KOREAN} "testscenariomaker:// URL 프로토콜을 등록합니다"

LangString DESC_SEC01 ${LANG_ENGLISH} "TestscenarioMaker CLI core executable and configuration files"
LangString DESC_SEC02 ${LANG_ENGLISH} "Add CLI tool path to system PATH environment variable"
LangString DESC_SEC03 ${LANG_ENGLISH} "Create desktop shortcut"
LangString DESC_SEC04 ${LANG_ENGLISH} "Create start menu shortcuts"
LangString DESC_SEC05 ${LANG_ENGLISH} "Register testscenariomaker:// URL protocol"

; 섹션 설명 할당
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
!insertmacro MUI_DESCRIPTION_TEXT ${SEC01} $(DESC_SEC01)
!insertmacro MUI_DESCRIPTION_TEXT ${SEC02} $(DESC_SEC02)
!insertmacro MUI_DESCRIPTION_TEXT ${SEC03} $(DESC_SEC03)
!insertmacro MUI_DESCRIPTION_TEXT ${SEC04} $(DESC_SEC04)
!insertmacro MUI_DESCRIPTION_TEXT ${SEC05} $(DESC_SEC05)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; 제거 섹션

Section "Uninstall"
  
  ; 파일 삭제
  Delete $INSTDIR\\ts-cli.exe
  Delete $INSTDIR\\config\\config.ini
  Delete $INSTDIR\\uninstall.exe
  
  ; 디렉토리 삭제
  RMDir $INSTDIR\\config
  RMDir $INSTDIR
  
  ; 바로가기 삭제
  Delete "$DESKTOP\\TestscenarioMaker CLI.lnk"
  Delete "$SMPROGRAMS\\TestscenarioMaker\\TestscenarioMaker CLI.lnk"
  Delete "$SMPROGRAMS\\TestscenarioMaker\\제거.lnk"
  RMDir "$SMPROGRAMS\\TestscenarioMaker"
  
  ; 레지스트리 정리
  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TestscenarioMaker CLI"
  DeleteRegKey HKLM "SOFTWARE\\TestscenarioMaker\\CLI"
  DeleteRegKey HKLM "SOFTWARE\\TestscenarioMaker"
  
  ; URL 프로토콜 제거
  DeleteRegKey HKCR "testscenariomaker"
  
  ; PATH에서 제거
  ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$INSTDIR"
  
SectionEnd

;--------------------------------
; 함수

; 환경변수 업데이트 매크로 포함
!include "EnvVarUpdate.nsh"

; 설치 초기화
Function .onInit
  ; 64비트 시스템 확인
  ${If} ${RunningX64}
    SetRegView 64
    StrCpy $INSTDIR "$PROGRAMFILES64\\TestscenarioMaker CLI"
  ${Else}
    StrCpy $INSTDIR "$PROGRAMFILES32\\TestscenarioMaker CLI"
  ${EndIf}
FunctionEnd

; 제거 초기화
Function un.onInit
  ${If} ${RunningX64}
    SetRegView 64
  ${EndIf}
FunctionEnd