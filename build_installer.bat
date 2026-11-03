@echo off
setlocal
cd /d "%~dp0"
title Compilar instalador PylandTweaks

echo ==========================================
echo    PylandTweaks - Build + Instalador
echo ==========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH.
    pause
    exit /b 1
)

echo [1/2] Generando ejecutable...
python -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin ^
    --name "PylandTweaks" ^
    --icon "assets\app.ico" ^
    --add-data "assets;assets" ^
    --add-data "Apariencia;Apariencia" ^
    --add-data "Recursos;Recursos" ^
    "Optimizador_GUI.py"
if errorlevel 1 goto :error

echo.
echo [2/2] Generando instalador...
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo ERROR: Inno Setup 6 no esta instalado.
    echo Instalalo con: winget install --id JRSoftware.InnoSetup -e
    pause
    exit /b 1
)

"%ISCC%" "installer\PylandTweaks.iss"
if errorlevel 1 goto :error

echo.
echo ==========================================
echo    Listo
echo    Ejecutable: dist\PylandTweaks.exe
echo    Instalador: installer\Output\PylandTweaks_Setup_5.8.exe
echo ==========================================
pause
exit /b 0

:error
echo.
echo Ocurrio un error.
pause
exit /b 1
