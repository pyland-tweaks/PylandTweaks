@echo off
setlocal
cd /d "%~dp0"
title Compilar PylandTweaks

echo ==========================================
echo    Compilando PylandTweaks a EXE
echo ==========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH.
    pause
    exit /b 1
)

echo Instalando dependencias de compilacion...
python -m pip install --upgrade pyinstaller pillow
if errorlevel 1 goto :error

echo.
echo Generando ejecutable...
python -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin ^
    --name "PylandTweaks" ^
    --icon "assets\app.ico" ^
    --add-data "assets;assets" ^
    --add-data "Apariencia;Apariencia" ^
    --add-data "Recursos;Recursos" ^
    "Optimizador_GUI.py"
if errorlevel 1 goto :error

echo.
echo ==========================================
echo    Listo: dist\PylandTweaks.exe
echo ==========================================
pause
exit /b 0

:error
echo.
echo Ocurrio un error durante la compilacion.
pause
exit /b 1
