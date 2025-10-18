@echo off
title Discord Gemini Bot - Runner
echo ----------------------------------------
echo Starting Discord Gemini Bot...
echo ----------------------------------------

:: Check if venv exists
if not exist "venv\" (
    echo No virtual environment found. Creating one...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate

:: Check if requirements are installed
if exist "venv\Scripts\pip.exe" (
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    echo Pip not found! Make sure Python and pip are installed properly.
    pause
    exit /b
)

:: Run the bot
echo Running bot...
python oldbot.py

:: Keep window open if bot crashes or exits
echo.
echo Bot has stopped. Press any key to close.
pause >nul
