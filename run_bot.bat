@echo off
title SmartStudentBot - Perugia Bot Runner
cd /d "%~dp0SmartStudentBot"

echo Starting SmartStudentBot

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    python main.py
)

pause
