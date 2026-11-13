@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ===============================================
echo   مدير شئون الطلاب Pro 2026/2027 - v2.3 - بناء ويندوز
echo ===============================================
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo لم يتم العثور على Python 3. يرجى تثبيت Python 3.11 أو 3.12 وتفعيل Add Python to PATH.
  pause
  exit /b 1
)
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name "StudentManagerPro2026" --collect-all qrcode student_manager.py
if errorlevel 1 goto :error
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
  "C:\Program Files (x86)\NSIS\makensis.exe" StudentManagerPro.nsi
) else if exist "C:\Program Files\NSIS\makensis.exe" (
  "C:\Program Files\NSIS\makensis.exe" StudentManagerPro.nsi
) else (
  echo.
  echo تم بناء البرنامج التنفيذي dist\StudentManagerPro2026.exe
  echo لم يتم العثور على NSIS؛ ثبّت NSIS ثم شغّل هذا الملف مرة أخرى لإنشاء Setup.exe.
  pause
  exit /b 0
)
if errorlevel 1 goto :error
echo.
echo اكتمل البناء: StudentManagerPro_Setup.exe
pause
exit /b 0
:error
echo حدث خطأ أثناء البناء. راجع الرسائل أعلاه.
pause
exit /b 1
