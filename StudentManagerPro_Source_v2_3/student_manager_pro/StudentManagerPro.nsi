Unicode True
Name "مدير شئون الطلاب Pro 2026/2027"
OutFile "StudentManagerPro_Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\StudentManagerPro"
RequestExecutionLevel user
SetCompressor /SOLID lzma

Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section "تثبيت مدير شئون الطلاب Pro"
  SetOutPath "$INSTDIR"
  File "dist\StudentManagerPro2026.exe"
  CreateDirectory "$SMPROGRAMS\مدير شئون الطلاب Pro"
  CreateShortcut "$SMPROGRAMS\مدير شئون الطلاب Pro\تشغيل البرنامج.lnk" "$INSTDIR\StudentManagerPro2026.exe"
  CreateShortcut "$DESKTOP\مدير شئون الطلاب Pro.lnk" "$INSTDIR\StudentManagerPro2026.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\StudentManagerPro" "DisplayName" "مدير شئون الطلاب Pro 2026/2027"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\StudentManagerPro" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\StudentManagerPro" "DisplayVersion" "2.3"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\مدير شئون الطلاب Pro.lnk"
  Delete "$SMPROGRAMS\مدير شئون الطلاب Pro\تشغيل البرنامج.lnk"
  RMDir "$SMPROGRAMS\مدير شئون الطلاب Pro"
  Delete "$INSTDIR\StudentManagerPro2026.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\StudentManagerPro"
  ; لا نحذف قاعدة البيانات الموجودة في مجلد المستخدم حتى لا تضيع بيانات المدرسة.
SectionEnd
