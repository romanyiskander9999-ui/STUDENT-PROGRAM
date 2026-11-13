@echo off
chcp 65001 >nul
cd /d "%~dp0"
title مدير شئون الطلاب Pro 2026/2027 - v2.1
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py") else (set "PY=python")
%PY% --version >nul 2>nul
if errorlevel 1 (
 echo لم يتم العثور على Python. ثبّت Python 3.10 أو أحدث مع تفعيل Add Python to PATH.
 pause
 exit /b 1
)
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
 echo تعذر تثبيت المتطلبات. تحقق من اتصال الإنترنت ثم أعد المحاولة.
 pause
 exit /b 1
)
%PY% student_manager.py
if errorlevel 1 pause
