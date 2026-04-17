@echo off
REM ===================================
REM Automated Metrics Collection Script
REM ===================================
REM This script collects system metrics every time it runs
REM Run this via Windows Task Scheduler

setlocal enabledelayexpansion

REM Set project directory
set PROJECT_DIR=C:\Users\HP\Documents\Training\radoki_im_system

REM Change to project directory
cd /d "%PROJECT_DIR%" || (
    echo Error: Could not navigate to project directory
    exit /b 1
)

REM Run metrics collection
echo Collecting system metrics at %date% %time%...
python manage.py collect_system_metrics

if %errorlevel% equ 0 (
    echo Metrics collected successfully
) else (
    echo Error collecting metrics - Exit Code: %errorlevel%
)

exit /b %errorlevel%
