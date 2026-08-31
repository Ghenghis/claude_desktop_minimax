"""Explicit, bounded MCP acceptance checks in a disposable workspace."""

import asyncio
from contextlib import AsyncExitStack
from datetime import timedelta
import argparse
import shutil
import subprocess
import tempfile
import json
import os
import re
import struct
import zlib
from pathlib import Path
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from configure_claude import core_servers

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--live", action="store_true", help="Permit the public docs and MiniMax API smoke calls")
parser.add_argument("--ssh-alias", help="Optional existing SSH alias; fixed read-only command, no host-key changes")
parser.add_argument("--server", help="Test one named core server")
options = parser.parse_args()
valid_servers = {"Windows-MCP", "project-files", "playwright", "context7", "minimax-coding-plan", "minimax"}
if options.server and options.server not in valid_servers:
    parser.error("--server must name one of the six configured core servers")
SCRATCH = Path(tempfile.mkdtemp(prefix="claude-mcp-acceptance-"))
NODE = shutil.which("node.exe")
if not NODE:
    raise SystemExit("Node.js is missing; no installation or repair was attempted")


def text_of(result):
    return "\n".join(x.text for x in result.content if x.type == "text")


async def check(entry, report):
    started = time.monotonic()
    name = entry["name"]
    env = {
        "SYSTEMROOT": os.environ["SYSTEMROOT"],
        "USERPROFILE": os.environ["USERPROFILE"],
        "APPDATA": os.environ["APPDATA"],
        "LOCALAPPDATA": os.environ["LOCALAPPDATA"],
        "TEMP": os.environ["TEMP"],
        "PATH": os.environ["PATH"],
        "PYTHONUTF8": "1",
        "ANONYMIZED_TELEMETRY": "false",
        "WINDOWS_MCP_WATCHDOG": "off",
    }
    row = {"server": name}
    report.append(row)
    with (SCRATCH / (name + ".stderr.log")).open("w", encoding="utf-8") as errlog:
        try:
            async with AsyncExitStack() as stack:
                streams = await stack.enter_async_context(
                    stdio_client(
                        StdioServerParameters(command=entry["command"], args=entry["args"], cwd=str(SCRATCH), env=env),
                        errlog=errlog,
                    )
                )
                session = await stack.enter_async_context(
                    ClientSession(*streams, read_timeout_seconds=timedelta(seconds=120))
                )
                info = await session.initialize()
                listing = await session.list_tools()
                row["version"] = info.serverInfo.version
                row["tools"] = [t.name for t in listing.tools]
                # Keep exact schemas locally for client integration tests; no secret values.
                (SCRATCH / (name + ".schemas.json")).write_text(listing.model_dump_json(indent=2), encoding="utf-8")
                if name == "Windows-MCP":
                    assert not {"PowerShell", "Process", "Registry", "FileSystem", "App", "Click", "Type",
                                "Scroll", "Move", "Shortcut"}.intersection(row["tools"])
                    for tool in listing.tools:
                        if tool.name.startswith("Window"):
                            assert {"window_handle", "window_title"}.issubset(tool.inputSchema.get("required", []))
                    assert {"WindowSetValue", "WindowInvoke", "InspectWindow"}.issubset(row["tools"])
                    result = await session.call_tool("Snapshot", {"use_vision": False, "use_ui_tree": False})
                    value = text_of(result)
                    assert not result.isError and "Error capturing" not in value, value[:100]
                    row["workflow"] = "Snapshot succeeded; process/shell/registry tools absent"
                    result = await session.call_tool(
                        "WindowClick", {"window_handle": 0, "window_title": "Invalid fixture", "x": 0, "y": 0}
                    )
                    assert result.isError, "Invalid window handle must never receive input"
                    row["workflow"] += "; invalid window input refused"
                elif name == "project-files":
                    for tool in listing.tools:
                        schema = tool.outputSchema or {}
                        assert schema.get("$schema") in (None, "https://json-schema.org/draft/2020-12/schema")
                    target = str(SCRATCH / "mcp-roundtrip.txt")
                    result = await session.call_tool("write_file", {"path": target, "content": "MCP round trip passed"})
                    assert not result.isError
                    result = await session.call_tool("read_text_file", {"path": target})
                    assert "MCP round trip passed" in text_of(result)
                    with tempfile.TemporaryDirectory(prefix="claude-outside-") as outside_dir:
                        outside = Path(outside_dir) / "sentinel.txt"
                        outside.write_text("must not be accessible through filesystem MCP")
                        result = await session.call_tool("read_text_file", {"path": str(outside)})
                    assert result.isError, "outside root unexpectedly readable"
                    row["workflow"] = "File write/read passed; outside-root read denied"
                elif name == "playwright":
                    result = await session.call_tool(
                        "browser_navigate", {"url": f"http://127.0.0.1:{WEB.server_address[1]}"}
                    )
                    assert not result.isError
                    result = await session.call_tool(
                        "browser_evaluate",
                        {
                            "function": ('() => { document.querySelector("button").click(); '
                                         'return document.body.innerText; }')
                        },
                    )
                    assert not result.isError and "BROWSER_TEST_PASSED" in text_of(result)
                    await session.call_tool("browser_close", {})
                    row["workflow"] = "Isolated headless browser loaded and operated local fixture"
                elif name in ("context7", "minimax-coding-plan", "minimax") and not options.live:
                    row["workflow"] = "Handshake and tool listing passed; live API call not requested"
                elif name == "context7":
                    result = await session.call_tool(
                        "resolve-library-id",
                        {"libraryName": "python", "query": "Python pathlib official documentation"},
                    )
                    assert not result.isError and len(text_of(result)) > 30
                    row["workflow"] = "Public documentation library resolution returned results"
                elif name == "minimax-coding-plan":
                    result = await session.call_tool("web_search", {"query": "Python pathlib official documentation"})
                    value = text_of(result)
                    assert not result.isError and not value.lower().startswith(("error", "failed")), value[:100]
                    row["workflow"] = "Live MiniMax web search returned results"
                    # Synthetic solid-color fixture only. Never upload a user screenshot/file.

                    def chunk(kind, data):
                        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

                    pixels = b"".join(b"\x00" + b"\xff\x00\x00" * 128 for _ in range(128))
                    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 128, 128, 8, 2, 0, 0, 0))
                    png += chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")
                    fixture = SCRATCH / "synthetic-red.png"
                    fixture.write_bytes(png)
                    result = await session.call_tool(
                        "understand_image", {"prompt": "What is the dominant color? Reply with one color in English.",
                                             "image_source": str(fixture)}
                    )
                    assert not result.isError and "red" in text_of(result).lower()
                    row["workflow"] += "; synthetic image correctly identified as red"
                elif name == "minimax":
                    tool = next(t for t in listing.tools if t.name == "list_voices")
                    props = tool.inputSchema.get("properties", {})
                    args = {"voice_type": "system"} if "voice_type" in props else {}
                    result = await session.call_tool("list_voices", args)
                    value = text_of(result)
                    assert not result.isError and not value.lower().startswith(("error", "failed")), value[:100]
                    row["workflow"] = "Live MiniMax voice catalogue returned results"
                row["status"] = "passed"
        except Exception as error:
            row["status"] = "failed"
            row["error"] = type(error).__name__  # Do not persist upstream error bodies or credentials.
            pending = [error]
            leaves = set()
            while pending:
                item = pending.pop()
                if isinstance(item, BaseExceptionGroup):
                    pending.extend(item.exceptions)
                else:
                    leaves.add(type(item).__name__)
            row["error_types"] = sorted(leaves)
    row["elapsed_seconds"] = round(time.monotonic() - started, 2)
    print(json.dumps(row), flush=True)


class Page(BaseHTTPRequestHandler):
    def do_GET(self):
        data = (b"<html><title>MCP isolated acceptance test</title><body>"
                b"<button onclick=\"this.innerText='BROWSER_TEST_PASSED'\">Test</button></body></html>")
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


WEB = ThreadingHTTPServer(("127.0.0.1", 0), Page)
threading.Thread(target=WEB.serve_forever, daemon=True).start()


async def main():
    report = []
    try:
        for entry in core_servers(SCRATCH, NODE):
            if options.server and entry["name"] != options.server:
                continue
            await check(entry, report)
        if options.ssh_alias:
            report.append(check_ssh(options.ssh_alias))
    finally:
        WEB.shutdown()
        WEB.server_close()
        (SCRATCH / "mcp-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Evidence:", SCRATCH / "mcp-results.json")
    if any(row["status"] != "passed" for row in report):
        raise SystemExit(1)


def check_ssh(alias):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", alias):
        raise ValueError("SSH alias must be a plain existing alias, not options or a command")
    command = shutil.which("ssh.exe")
    row = {"server": "native-openssh", "status": "failed"}
    if not command:
        return row
    try:
        result = subprocess.run(
            [
                command,
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=yes",
                "-o",
                "ConnectTimeout=8",
                alias,
                "uname -s; id -un",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines = result.stdout.splitlines()
        row["status"] = "passed" if result.returncode == 0 and len(lines) >= 2 else "failed"
        row["workflow"] = "Read-only SSH OS/account query; no remote changes"
        row["root_account"] = len(lines) >= 2 and lines[-1] == "root"
    except (OSError, subprocess.TimeoutExpired) as error:
        row["error"] = type(error).__name__
    print(json.dumps(row), flush=True)
    return row


if __name__ == "__main__":
    asyncio.run(main())
