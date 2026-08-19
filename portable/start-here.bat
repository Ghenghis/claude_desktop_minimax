@echo off
:: One-click Windows launcher for the Claude-Desktop MiniMax V2 portable bundle.
:: Double-click this file on any Windows 11 PC.  It runs install.ps1 and then
:: starts the gateway if the installation checks pass.

echo ******************************************
echo  Claude Desktop  MiniMax V2  Portable
echo ******************************************
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if %errorlevel% neq 0 (
    echo.
    echo Setup failed. See the messages above.
    pause
    exit /b %errorlevel%
)

echo.
echo Starting the MiniMax V2 gateway...
powershell -ExecutionPolicy Bypass -File "%~dp0..\Start-ClaudeMinimaxV2.ps1"

pause
