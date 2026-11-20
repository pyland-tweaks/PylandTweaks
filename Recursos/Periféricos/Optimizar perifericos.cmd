@echo off
setlocal
cd /d "%~dp0..\.."
title PylandTweaks - Perifericos

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH.
    pause
    exit /b 1
)

:menu
cls
echo.
echo --------------------------------------------------
echo            PylandTweaks - Perifericos
echo --------------------------------------------------
echo.
echo   1) Optimizar (perfil competitivo)
echo   2) Optimizar (perfil clasico 2/120)
echo   3) Restaurar valores originales
echo   4) Salir
echo.
set /p op=Opcion:
if "%op%"=="1" python perifericos.py apply competitivo
if "%op%"=="2" python perifericos.py apply clasico_2_120
if "%op%"=="3" python perifericos.py restore
if "%op%"=="4" exit /b 0
pause
goto :menu
