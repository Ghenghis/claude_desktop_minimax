"""Direct, shell-free entry points for pinned Python MCP packages.

No child supervisor, install-on-connect, periodic checks, or automatic repair.
Run with the corresponding isolated environment's pythonw.exe on Windows.
"""

import argparse
import importlib
import os
from pathlib import Path
import sys

from gateway_common import parse_dotenv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("server", choices=("windows", "minimax", "minimax-plan"))
    args, remainder = parser.parse_known_args()
    if args.server == "windows":
        os.environ["WINDOWS_MCP_WATCHDOG"] = "off"
        os.environ["WINDOWS_MCP_MAX_TREE_ELEMENTS"] = "500"
        os.environ["ANONYMIZED_TELEMETRY"] = "false"
        sys.argv = [
            "windows-mcp",
            "serve",
            "--tools",
            "Snapshot,Screenshot,InspectWindow,WindowSetValue,WindowInvoke,WindowClick,WindowType,"
            "WindowScroll,WindowMove,WindowShortcut,Wait,WaitFor",
            *remainder,
        ]
        from windows_mcp import __main__ as windows
        from mcp_windows import register_window_inspection

        register_window_inspection(windows._build_mcp(), windows._get_desktop)
        windows.main()
        return
    # Only pass the one required secret, never all keys from a shared .env.
    private = Path(os.environ.get("MINIMAX_ENV_FILE", r"C:\private\.env"))
    key = os.environ.get("MINIMAX_API_KEY") or parse_dotenv(private.read_text(encoding="utf-8-sig")).get(
        "MINIMAX_API_KEY"
    )
    if not key:
        raise RuntimeError("MiniMax credential unavailable")
    os.environ["MINIMAX_API_KEY"] = key
    os.environ["MINIMAX_API_HOST"] = "https://api.minimax.io"
    os.environ.setdefault("MINIMAX_MCP_BASE_PATH", str(Path.home() / "MiniMax-Generated"))
    os.environ["MINIMAX_API_RESOURCE_MODE"] = "local"
    sys.argv = ["minimax-mcp", *remainder]
    module = importlib.import_module("minimax_mcp.server")
    # The official main() prints a banner to stdout. MCP stdout must be JSON-RPC only.
    module.mcp.run()


if __name__ == "__main__":
    main()
