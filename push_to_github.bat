@echo off
title Push Perugia Bot to GitHub
cd /d "%~dp0"

echo ====================================================
echo Configuring Git Author Identity...
echo ====================================================

git config user.name "agha-seyed"
git config user.email "agha-seyed@users.noreply.github.com"

echo ====================================================
echo Staging and Committing Perugia Bot to GitHub...
echo ====================================================

git add .
git commit -m "fix: resolve isee_handler syntax, optimize render startup, add mongodb and upstash redis support"

echo.
echo Pushing to origin main...
git push origin main

echo.
if %errorlevel% equ 0 (
    echo ====================================================
    echo [SUCCESS] Successfully pushed to GitHub!
    echo Now click 'Retry' on Render.com to proceed.
    echo ====================================================
) else (
    echo ====================================================
    echo [ERROR] Git push failed. Please check your credentials or internet.
    echo ====================================================
)

exit /b 0
