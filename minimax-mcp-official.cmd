@echo off
rem Legacy explicit CLI wrapper. Desktop uses pythonw directly, without cmd.
"%~dp0venvs\minimax-mcp\Scripts\python.exe" "%~dp0mcp_launcher.py" minimax
exit /b %errorlevel%
