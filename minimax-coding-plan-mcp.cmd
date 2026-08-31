@echo off
rem Legacy explicit CLI wrapper. Desktop uses pythonw directly, without cmd.
"%~dp0venvs\minimax-plan\Scripts\python.exe" "%~dp0mcp_launcher.py" minimax-plan
exit /b %errorlevel%
