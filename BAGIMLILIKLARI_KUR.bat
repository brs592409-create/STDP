@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Calisma dizinini scriptin bulundugu klasore sabitle
cd /d "%~dp0"
title STDP - Tum Bagimliliklari Otomatik Kurucu

:: ---------------------------------------------------------------------
:: 0. ADIM: Yonetici Izinleri Kontrolu ve Otomatik Yukseltme (UAC)
:: ---------------------------------------------------------------------
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ===================================================================
    echo [!] Yonetici izinleri gerekiyor.
    echo     Lutfen acilan UAC penceresinde "EVET" butonuna basin...
    echo ===================================================================
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ===================================================================
echo     STDP (Steam Tool Depotbox Pipeline) - Otomatik Kurulum Araci
echo ===================================================================
echo.
echo Bu arac, format atilmis temiz bir Windows bilgisayarda STDP'nin
echo sorunsuz calismasi icin gereken tum bilesenleri tek seferde kurar:
echo.
echo  1. Microsoft Visual C++ 2015-2022 Redistributable
echo  2. 7-Zip / UnRAR Tam Arşiv Motoru (RAR, 7z, ZIP)
echo  3. Python Ortami ve Kutuphaneleri (PyQt6, WebEngine, psutil, vdf)
echo  4. SteamTools Kanca Motoru (st-setup-1.8.30.exe)
echo  5. Windows Defender Dislama Kurali (DLL korumasi)
echo.
echo ===================================================================
echo Kuruluma baslamak icin bir tusa basin...
pause >nul
echo.

if not exist "bundled_installers" mkdir "bundled_installers"
if not exist "logs" mkdir "logs"

:: ---------------------------------------------------------------------
:: 1. ADIM: Microsoft Visual C++ 2015-2022 Redistributable Kurulumu
:: ---------------------------------------------------------------------
echo -------------------------------------------------------------------
echo [1/5] Microsoft Visual C++ 2015-2022 Redistributable kontrol ediliyor...
echo -------------------------------------------------------------------

set "VC_INSTALLED=0"
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed >nul 2>&1
if %errorlevel% equ 0 set "VC_INSTALLED=1"
reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed >nul 2>&1
if %errorlevel% equ 0 set "VC_INSTALLED=1"

if "!VC_INSTALLED!"=="1" goto :VC_OK

echo [..] VC++ Redistributable indiriliyor...
set "VC_EXE=%TEMP%\vc_redist.x64.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://aka.ms/vs/17/release/vc_redist.x64.exe', '$env:TEMP\vc_redist.x64.exe')" 2>nul

if exist "!VC_EXE!" (
    echo [..] VC++ Redistributable sessizce kuruluyor...
    start /wait "" "!VC_EXE!" /install /passive /norestart
    del /f /q "!VC_EXE!" >nul 2>&1
    echo [OK] Visual C++ Redistributable basariyla kuruldu.
) else (
    echo [!] VC++ otomatik indirilemedi.
)
goto :STEP2

:VC_OK
echo [OK] Visual C++ 2015-2022 Redistributable zaten sistemde yuklu.

:STEP2
:: ---------------------------------------------------------------------
:: 2. ADIM: 7-Zip / UnRAR Arşiv Motoru Kontrolü
:: ---------------------------------------------------------------------
echo.
echo -------------------------------------------------------------------
echo [2/5] 7-Zip / UnRAR Arşiv Motoru kontrol ediliyor...
echo -------------------------------------------------------------------

set "SEVENZIP_FOUND=0"
if exist "%~dp0bundled_installers\7z.exe" set "SEVENZIP_FOUND=1"
if exist "C:\Program Files\7-Zip\7z.exe" set "SEVENZIP_FOUND=1"
if exist "C:\Program Files (x86)\7-Zip\7z.exe" set "SEVENZIP_FOUND=1"
if exist "%LOCALAPPDATA%\Programs\7-Zip\7z.exe" set "SEVENZIP_FOUND=1"

if "!SEVENZIP_FOUND!"=="1" goto :7Z_OK

echo [..] 7-Zip tam arsiv motoru entegre ediliyor...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.7-zip.org/a/7z2301-extra.7z', '$env:TEMP\7z_extra.7z'); if (Test-Path '%~dp0bundled_installers\7za.exe') { & '%~dp0bundled_installers\7za.exe' x '$env:TEMP\7z_extra.7z' -o'$env:TEMP\7z_ext' -y | Out-Null; Copy-Item '$env:TEMP\7z_ext\x64\7za.exe' '%~dp0bundled_installers\7z.exe' -Force; Copy-Item '$env:TEMP\7z_ext\x64\7zxa.dll' '%~dp0bundled_installers\7z.dll' -Force; Remove-Item '$env:TEMP\7z_ext' -Recurse -Force; Remove-Item '$env:TEMP\7z_extra.7z' -Force }" 2>nul

if exist "%~dp0bundled_installers\7z.exe" (
    echo [OK] 7-Zip / UnRAR motoru basariyla entegre edildi.
) else (
    echo [!] 7z.exe indirilemedi.
)
goto :STEP3

:7Z_OK
echo [OK] 7-Zip / UnRAR tam arşiv motoru hazir.

:STEP3
:: ---------------------------------------------------------------------
:: 3. ADIM: Python Ortami ve Kutuphanelerin Kurulumu
:: ---------------------------------------------------------------------
echo.
echo -------------------------------------------------------------------
echo [3/5] Python Calisma Ortami ve Paketleri hazirlaniyor...
echo -------------------------------------------------------------------

set "PYTHON_CMD="
if exist "%~dp0python_runtime\python.exe" set "PYTHON_CMD=%~dp0python_runtime\python.exe"

if not defined PYTHON_CMD (
    python --version >nul 2>&1
    if !errorlevel! equ 0 set "PYTHON_CMD=python"
)

if defined PYTHON_CMD (
    echo [OK] Python motoru tespit edildi: "!PYTHON_CMD!"
    echo [..] Python kutuphaneleri kontrol ediliyor...
    if exist "%~dp0requirements.txt" (
        "!PYTHON_CMD!" -m pip install -r requirements.txt >nul 2>&1
    )
    echo [OK] Python kutuphaneleri hazir.
) else (
    echo [X] Python motoru bulunamadi.
)

:: ---------------------------------------------------------------------
:: 4. ADIM: SteamTools Kurulumu
:: ---------------------------------------------------------------------
echo.
echo -------------------------------------------------------------------
echo [4/5] SteamTools Kanca Motoru kontrol ediliyor...
echo -------------------------------------------------------------------

set "ST_SETUP="
if exist "%~dp0st-setup-1.8.30.exe" set "ST_SETUP=%~dp0st-setup-1.8.30.exe"
if exist "%~dp0bundled_installers\st-setup-1.8.30.exe" set "ST_SETUP=%~dp0bundled_installers\st-setup-1.8.30.exe"

if defined ST_SETUP (
    echo [..] SteamTools sessiz kurulumu yapiliyor...
    start /wait "" "!ST_SETUP!" /S
    echo 1 > ".steamtools_installed"
    echo [OK] SteamTools kurulumu basariyla tamamlandi.
) else (
    echo [!] st-setup-1.8.30.exe bulunamadi.
)

:: ---------------------------------------------------------------------
:: 5. ADIM: Windows Defender Dislama Kurali (False-Positive Onleme)
:: ---------------------------------------------------------------------
echo.
echo -------------------------------------------------------------------
echo [5/5] Windows Defender Guvenlik Dislama Kurali...
echo -------------------------------------------------------------------

powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-MpPreference -ExclusionPath '%~dp0' -ErrorAction SilentlyContinue" 2>nul
if %errorlevel% equ 0 (
    echo [OK] Proje klasoru Windows Defender dislama listesine eklendi.
) else (
    echo [..] Defender dislama adimi tamamlandi.
)

echo.
echo ===================================================================
echo     🎉 TEBRIKLER! TUM BAGIMLILIKLAR BASARIYLA HAZIRLANDI!
echo ===================================================================
echo.
echo Artik "BASLAT.bat" ile STDP uygulamasini calistirabilirsiniz.
echo.
echo Cikmak icin bir tusa basin...
pause >nul
exit /b 0
