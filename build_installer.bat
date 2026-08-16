@echo off
setlocal enabledelayedexpansion
title STDP Installer Builder
echo.
echo ============================================================
echo   STDP Installer Builder
echo   Tum bagimliliklari paketleyip tek bir installer olusturur
echo ============================================================
echo.

:: ---- Step 0: Check Python ----
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python bulunamadi! Lutfen Python 3.11+ kurun.
    pause
    exit /b 1
)
echo [OK] Python bulundu.

:: ---- Step 1: Install Python dependencies ----
echo.
echo [1/5] Python bagimliliklari kuruluyor...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [X] Bagimlilik kurulumu basarisiz!
    pause
    exit /b 1
)
echo [OK] Python bagimliliklari kuruldu.

:: ---- Step 2: Install PyInstaller ----
echo.
echo [2/5] PyInstaller kontrol ediliyor...
pip install pyinstaller --quiet
echo [OK] PyInstaller hazir.

:: ---- Step 3: Build EXE with PyInstaller ----
echo.
echo [3/5] PyInstaller ile EXE olusturuluyor...
echo       (Bu islem birkac dakika surebilir)
python build_exe.py
if errorlevel 1 (
    echo [X] PyInstaller build basarisiz!
    pause
    exit /b 1
)
echo [OK] STDP.exe basariyla olusturuldu.

:: ---- Step 4: Ensure st-setup in bundled_installers ----
echo.
echo [4/5] st-setup-1.8.30.exe kontrol ediliyor...
if not exist "bundled_installers" mkdir "bundled_installers"

if exist "%~dp0st-setup-1.8.30.exe" (
    copy /Y "%~dp0st-setup-1.8.30.exe" "bundled_installers\st-setup-1.8.30.exe" >nul
    echo [OK] st-setup-1.8.30.exe bundled_installers klasorune kopyalandi.
) else if exist "bundled_installers\st-setup-1.8.30.exe" (
    echo [OK] bundled_installers\st-setup-1.8.30.exe zaten mevcut.
) else (
    echo [!] st-setup-1.8.30.exe bulunamadi!
    pause
    exit /b 1
)

:: ---- Step 5: Compile Inno Setup installer ----
echo.
echo [5/5] Inno Setup ile installer derleniyor...

:: Try common Inno Setup paths
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if "!ISCC!"=="" (
    echo [!] Inno Setup bulunamadi!
    echo     Lutfen https://jrsoftware.org/isdl.php adresinden
    echo     Inno Setup 6 kurun ve bu script'i tekrar calistirin.
    echo.
    echo     Not: PyInstaller build basarili. dist\STDP\ klasorunu
    echo     dogrudan dagitabilirsiniz, ancak installer icin Inno Setup gerekli.
    pause
    exit /b 1
)

if not exist "installer_output" mkdir "installer_output"
"!ISCC!" stdp_installer.iss
if errorlevel 1 (
    echo [X] Inno Setup derleme basarisiz!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   [OK] BASARILI!
echo   Installer: installer_output\STDP_Setup.exe
echo ============================================================
echo.
pause
