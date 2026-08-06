@echo off
title MediExtractAI Server Manager
echo ===================================================
echo   MediExtractAI - Launching Local Servers
echo ===================================================
echo.

:: 1. Check and start MariaDB on port 3307
echo [1/2] Launching XAMPP MySQL database on port 3307...
tasklist /FI "IMAGENAME eq mysqld.exe" 2>NUL | find /I /N "mysqld.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Database server is already running.
) else (
    start /B "" "C:\xampp1\mysql\bin\mysqld.exe" --defaults-file="C:\xampp1\mysql\bin\my.ini" --standalone >nul 2>&1
    echo Database server started successfully.
)
timeout /t 3 /nobreak >nul
echo.

:: 2. Launch Flask Application on port 5000
echo [2/2] Launching Flask NLP Server on http://127.0.0.1:5000 ...
cd /d "C:\xampp1\htdocs\Prescription\MediExtractAI"
"..\.venv\Scripts\python.exe" app.py

pause
