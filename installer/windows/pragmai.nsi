Unicode True
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinMessages.nsh"

!ifndef APP_VERSION
  !error "APP_VERSION is required."
!endif
!ifndef APP_EXE
  !error "APP_EXE is required."
!endif
!ifndef OUTPUT_DIR
  !error "OUTPUT_DIR is required."
!endif

!define PRODUCT_NAME "PragmAI"
!define PRODUCT_PUBLISHER "PragmAI"
!define PRODUCT_URL "https://m-pragm-ai.vercel.app"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\PragmAI"
!define APP_PATH_KEY "Software\Microsoft\Windows\CurrentVersion\App Paths\pragmai.exe"

Name "${PRODUCT_NAME}"
OutFile "${OUTPUT_DIR}\pragmai-windows-x64-setup.exe"
InstallDir "$LOCALAPPDATA\Programs\PragmAI"
InstallDirRegKey HKCU "${UNINSTALL_KEY}" "InstallLocation"
RequestExecutionLevel user
ManifestDPIAware true
ShowInstDetails show
ShowUninstDetails show
BrandingText "PragmAI"

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey /LANG=1033 "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey /LANG=1033 "FileDescription" "PragmAI installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "PragmAI Core contributors"

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "../../LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\pragmai.exe"
!define MUI_FINISHPAGE_RUN_PARAMETERS "setup"
!define MUI_FINISHPAGE_RUN_TEXT "Configure PragmAI now"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Function BroadcastEnvironmentChange
  SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
FunctionEnd

Function AddToUserPath
  ReadRegDWORD $4 HKCU "${UNINSTALL_KEY}" "PathAdded"
  nsExec::ExecToStack "$\"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe$\" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $\"$INSTDIR\update_user_path.ps1$\" -Action Add -Directory $\"$INSTDIR$\""
  Pop $0
  Pop $1
  StrCmp $0 10 path_added
  StrCmp $0 0 path_present path_failed

path_added:
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "PathAdded" 1
  Call BroadcastEnvironmentChange
  Return

path_present:
  StrCmp $4 1 path_done
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "PathAdded" 0
path_done:
  Return

path_failed:
  SetErrors
FunctionEnd

Section "PragmAI" SEC_MAIN
  SectionIn RO
  SetOutPath "$INSTDIR"
  SetOverwrite on
  File /oname=pragmai.exe "${APP_EXE}"
  File /oname=update_user_path.ps1 "update_user_path.ps1"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "URLInfoAbout" "${PRODUCT_URL}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\pragmai.exe"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1

  WriteRegStr HKCU "${APP_PATH_KEY}" "" "$INSTDIR\pragmai.exe"
  WriteRegStr HKCU "${APP_PATH_KEY}" "Path" "$INSTDIR"
  ClearErrors
  Call AddToUserPath
  IfErrors path_setup_failed path_setup_done

path_setup_failed:
  DeleteRegKey HKCU "${APP_PATH_KEY}"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  Delete "$INSTDIR\pragmai.exe"
  Delete "$INSTDIR\update_user_path.ps1"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  MessageBox MB_ICONSTOP|MB_OK "PragmAI could not be added to the user PATH. Installation was cancelled."
  SetErrorLevel 1
  Abort
path_setup_done:
SectionEnd

Function un.BroadcastEnvironmentChange
  SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
FunctionEnd

Function un.RemoveFromUserPath
  ReadRegDWORD $4 HKCU "${UNINSTALL_KEY}" "PathAdded"
  StrCmp $4 1 0 path_done
  IfFileExists "$INSTDIR\update_user_path.ps1" 0 path_done
  nsExec::ExecToLog "$\"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe$\" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $\"$INSTDIR\update_user_path.ps1$\" -Action Remove -Directory $\"$INSTDIR$\""
  Call un.BroadcastEnvironmentChange
path_done:
FunctionEnd

Section "Uninstall"
  IfFileExists "$INSTDIR\pragmai.exe" 0 +2
  nsExec::ExecToLog "$\"$INSTDIR\pragmai.exe$\" uninstall"

  Call un.RemoveFromUserPath
  DeleteRegKey HKCU "${APP_PATH_KEY}"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  Delete "$INSTDIR\pragmai.exe"
  Delete "$INSTDIR\update_user_path.ps1"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
