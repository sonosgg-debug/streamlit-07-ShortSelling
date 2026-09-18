@echo off
title KRX Short Selling Dashboard (Streamlit)

echo ========================================================
echo  KRX Short Selling Dashboard - Local Server
echo  Address: http://localhost:8501
echo ========================================================
echo.

cd /d "%~dp0"

REM Activate virtual environment if present
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run Streamlit
python -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo [Error] Failed to run the application.
    pause
)
