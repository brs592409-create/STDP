@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"
title STDP - Izole Test Calistirici

echo ===================================================================
echo   IZOLE TEST ORTAMI (Sanal Arkadas Bilgisayari Simulasyonu)
echo ===================================================================
echo.
echo [i] Bu test; sisteminizdeki Python, ortam degiskenleri ve kurulu
echo     ayarlari tamamen gizleyerek uygulamayi sifir bir arkadas
echo     bilgisayarindaymis gibi calistirir.
echo.

:: 1. Sistem PATH'ini sifirla (Python'u gizle)
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"

:: 2. Gecici sahte kullanici profili ata (Sanki yeni bir kullanici gibi)
set "TEST_TEMP_DIR=%TEMP%\STDP_Isolated_Test"
if exist "%TEST_TEMP_DIR%" rmdir /s /q "%TEST_TEMP_DIR%" >nul 2>&1
mkdir "%TEST_TEMP_DIR%\AppData\Roaming" >nul 2>&1
mkdir "%TEST_TEMP_DIR%\AppData\Local" >nul 2>&1

set "USERPROFILE=%TEST_TEMP_DIR%"
set "APPDATA=%TEST_TEMP_DIR%\AppData\Roaming"
set "LOCALAPPDATA=%TEST_TEMP_DIR%\AppData\Local"

echo [i] PATH sifirlandi ve izole profil olusturuldu.
echo [i] BASLAT.bat test ediliyor...
echo.

call BASLAT.bat

echo.
echo ===================================================================
echo [i] Gecici test verileri temizleniyor...
rmdir /s /q "%TEST_TEMP_DIR%" >nul 2>&1
echo [OK] Test tamamlandi!
echo ===================================================================
pause
