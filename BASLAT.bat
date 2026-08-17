@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Calisma dizinini scriptin bulundugu klasore sabitle
cd /d "%~dp0"
title STDP - Steam Tool Depotbox Pipeline (Portable)

:: ---------------------------------------------------------------------
:: 0. ADIM: Yonetici Izinleri Kontrolu ve Otomatik Yukseltme (UAC)
:: ---------------------------------------------------------------------
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [..] Yonetici izinleri talep ediliyor, lutfen acilan pencereye EVET deyin...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

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
:: 2. ADIM: SteamTools Kurulum Kontrolu
:: ---------------------------------------------------------------------
echo.
echo [2/3] SteamTools kontrol ediliyor...

set "ST_INSTALLED=0"
if exist "%APPDATA%\SteamTools" set "ST_INSTALLED=1"
if exist "%LOCALAPPDATA%\Programs\SteamTools" set "ST_INSTALLED=1"
if exist "C:\Program Files (x86)\SteamTools" set "ST_INSTALLED=1"
if exist "C:\Program Files\SteamTools" set "ST_INSTALLED=1"
if exist ".steamtools_installed" set "ST_INSTALLED=1"

if "!ST_INSTALLED!"=="1" (
    echo [OK] SteamTools zaten kurulu.
) else (
    set "ST_SETUP="
    if exist "%~dp0st-setup-1.8.30.exe" set "ST_SETUP=%~dp0st-setup-1.8.30.exe"
    if exist "%~dp0bundled_installers\st-setup-1.8.30.exe" set "ST_SETUP=%~dp0bundled_installers\st-setup-1.8.30.exe"

    if defined ST_SETUP (
        echo [..] SteamTools otomatik kuruluyor, lutfen bekleyin...
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '!ST_SETUP!' -ArgumentList '/S' -Verb RunAs -Wait" 2>nul
        if errorlevel 1 (
            start /wait "" "!ST_SETUP!" /S
        )
        echo [OK] SteamTools kurulumu tamamlandi.
        echo 1 > ".steamtools_installed"
    ) else (
        echo [!] st-setup-1.8.30.exe bulunamadi, SteamTools adimi atlandi.
    )
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
