@echo off
REM Daily run — point Windows Task Scheduler at this file.
cd /d "%~dp0"
python hunter.py >> data\run.log 2>&1
