@echo off
rem Starts the Best View Glazing dashboard and opens it in the browser. Close this window (or press Ctrl+C) to stop it.
cd /d "%~dp0"
python -m pip install -q -r requirements.txt
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8787"
python run.py
pause
