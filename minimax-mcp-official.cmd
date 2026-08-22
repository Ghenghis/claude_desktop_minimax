@echo off
rem Launcher for the official MiniMax-MCP server (isolated venv).
rem Loads secrets from C:\private\.env, then starts the stdio MCP server.
setlocal
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("C:\private\.env") do set "%%a=%%b"
if not defined MINIMAX_API_KEY (
  echo MINIMAX_API_KEY missing from C:\private\.env 1>&2
  exit /b 1
)
set "MINIMAX_API_HOST=https://api.minimax.io"
set "MINIMAX_MCP_BASE_PATH=C:\Users\Admin\MiniMax-Generated"
set "MINIMAX_API_RESOURCE_MODE=local"
"C:\Users\Admin\claude-codex-devin\venvs\minimax-mcp\Scripts\minimax-mcp.exe" %*
