@echo off
rem Local pinned MiniMax Coding Plan MCP: web search + image understanding.
setlocal
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("C:\private\.env") do set "%%a=%%b"
if not defined MINIMAX_API_KEY (
  echo MINIMAX_API_KEY missing from C:\private\.env 1>&2
  exit /b 1
)
set "MINIMAX_API_HOST=https://api.minimax.io"
"C:\Users\Admin\claude-codex-devin\venvs\minimax-plan\Scripts\minimax-coding-plan-mcp.exe" -y %*
