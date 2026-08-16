@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Calisma dizinini scriptin bulundugu klasore sabitle
cd /d "%~dp0"
title STDP - Steam Tool Depotbox Pipeline (Portable)

echo.
echo ===================================================================
echo     STDP (Steam Tool Depotbox Pipeline) - Portable Baslatici
echo ===================================================================
echo.

:: ---------------------------------------------------------------------
:: 1. ADIM: Portable Python Calisma Ortami Tespiti
:: ---------------------------------------------------------------------
echo [1/3] Portable Python ortami hazirlaniyor...

set "PYTHON_EXE="

:: 1. Proje icindeki bagimsiz portable Python kontrolu (Oncelikli)
if exist "%~dp0python_runtime\python.exe" (
    set "PYTHON_EXE=%~dp0python_runtime\python.exe"
    goto :PYTHON_READY
)

:: 2. Fallback: Sistemdeki Python'u ara
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%I in ('python -c "import sys; print(sys.executable)"') do (
        set "PYTHON_EXE=%%I"
        goto :PYTHON_READY
    )
)

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)"') do (
        set "PYTHON_EXE=%%I"
        goto :PYTHON_READY
    )
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :PYTHON_READY
)
if exist "C:\Program Files\Python311\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python311\python.exe"
    goto :PYTHON_READY
)

:PYTHON_READY
if not defined PYTHON_EXE (
    echo [X] Python calisma motoru bulunamadi!
    echo     Lutfen python_runtime klasorunun mevcut oldugundan emin olun.
    pause
    exit /b 1
)

echo [OK] Portable Python motoru aktif: "%PYTHON_EXE%"

:: ---------------------------------------------------------------------
:: 2. ADIM: SteamTools Kilit Motoru Kontrolu ve Baslatma
:: ---------------------------------------------------------------------
echo.
echo [2/3] SteamTools kilit motoru kontrol ediliyor...

set "ST_EXE="
if exist "C:\Program Files (x86)\SteamTools\SteamTools.exe" set "ST_EXE=C:\Program Files (x86)\SteamTools\SteamTools.exe"
if exist "C:\Program Files\SteamTools\SteamTools.exe" set "ST_EXE=C:\Program Files\SteamTools\SteamTools.exe"
if exist "%LOCALAPPDATA%\Programs\SteamTools\SteamTools.exe" set "ST_EXE=%LOCALAPPDATA%\Programs\SteamTools\SteamTools.exe"
if exist "%LOCALAPPDATA%\SteamTools\SteamTools.exe" set "ST_EXE=%LOCALAPPDATA%\SteamTools\SteamTools.exe"
if exist "%APPDATA%\SteamTools\SteamTools.exe" set "ST_EXE=%APPDATA%\SteamTools\SteamTools.exe"

if not defined ST_EXE (
    set "ST_SETUP="
    if exist "%~dp0st-setup-1.8.30.exe" set "ST_SETUP=%~dp0st-setup-1.8.30.exe"
    if exist "%~dp0bundled_installers\st-setup-1.8.30.exe" set "ST_SETUP=%~dp0bundled_installers\st-setup-1.8.30.exe"

    if defined ST_SETUP (
        echo [..] SteamTools ilk kez kuruluyor, lutfen bekleyin...
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '!ST_SETUP!' -ArgumentList '/S' -Verb RunAs -Wait" 2>nul
        if errorlevel 1 (
            start /wait "" "!ST_SETUP!" /S
        )
        echo [OK] SteamTools kurulumu tamamlandi.
        
        if exist "C:\Program Files (x86)\SteamTools\SteamTools.exe" set "ST_EXE=C:\Program Files (x86)\SteamTools\SteamTools.exe"
        if exist "C:\Program Files\SteamTools\SteamTools.exe" set "ST_EXE=C:\Program Files\SteamTools\SteamTools.exe"
        if exist "%LOCALAPPDATA%\Programs\SteamTools\SteamTools.exe" set "ST_EXE=%LOCALAPPDATA%\Programs\SteamTools\SteamTools.exe"
        if exist "%LOCALAPPDATA%\SteamTools\SteamTools.exe" set "ST_EXE=%LOCALAPPDATA%\SteamTools\SteamTools.exe"
    )
)

:: SteamTools.exe'nin calisip calismadigini kontrol et ve arka planda baslat
if defined ST_EXE (
    tasklist /fi "imagename eq SteamTools.exe" 2>nul | find /i "SteamTools.exe" >nul
    if errorlevel 1 (
        echo [..] SteamTools kilit motoru arka planda baslatiliyor...
        start "" "!ST_EXE!"
        timeout /t 2 /nobreak >nul
    )
    echo [OK] SteamTools kilit motoru aktif.
) else (
    echo [!] SteamTools bulunamadi. STDP arayuzunden 'Teshis ^& Saglik' sekmesini kullanarak kurabilirsiniz.
)

if not exist "logs" mkdir "logs"

:: ---------------------------------------------------------------------
:: 3. ADIM: STDP Uygulamasini Baslat
:: ---------------------------------------------------------------------
echo.
echo [3/3] STDP Uygulamasi baslatiliyor...
echo ===================================================================
echo.

"%PYTHON_EXE%" main.py

if %errorlevel% neq 0 (
    echo.
    echo ===================================================================
    echo [!] Uygulama kapandi veya bir hata olustu.
    echo     Hata kayitlari: logs\stdp.log
    echo ===================================================================
    pause
)
