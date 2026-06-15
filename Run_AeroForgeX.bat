@echo off
color 0B
title AeroForgeX v3.0 - Multidisciplinary Optimization Matrix
cd /d "%~dp0"

echo ===============================================================================
echo   AeroForgeX :: High-Fidelity Airfoil Optimization Engine
echo   Version 3.0 (Neural/CST/Parallel)
echo ===============================================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ FATAL ] Python runtime not detected in system PATH.
    pause
    exit /b
)

python AeroForgeX_scr\aeroforgex_cli.py -i json_Input/Input_template.json
if %errorlevel% neq 0 (
    echo.
    echo [ FATAL ] Optimization matrix terminated due to an internal fault.
) else (
    echo.
    echo [ PASS ] Optimization matrix completed successfully.
)

echo.
pause