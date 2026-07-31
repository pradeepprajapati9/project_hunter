@echo off
REM Roz chalane ke liye — Task Scheduler me isi file ko daalo.
cd /d "%~dp0"
python hunter.py >> data\run.log 2>&1
