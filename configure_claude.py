"""Explicit profile changes with backups. Does not start/stop any application."""

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid
import winreg

ROOT = Path(__file__).resolve().parent


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def core_servers(workspace, node):
    runtime = ROOT / "mcp-runtime/node_modules"
    launcher = str(ROOT / "mcp_launcher.py")
    entries = [
        ("Windows-MCP", ROOT / "venvs/windows-mcp/Scripts/pythonw.exe", [launcher, "windows"]),
        (
            "project-files",
            node,
            [str(ROOT / "mcp-runtime/filesystem.mjs"), str(workspace)],
        ),
        (
            "playwright",
            node,
            [
                str(runtime / "@playwright/mcp/cli.js"),
                "--headless",
                "--isolated",
                "--browser",
                "msedge",
                "--output-dir",
                str(workspace / ".browser-output"),
            ],
        ),
        ("context7", node, [str(runtime / "@upstash/context7-mcp/dist/index.js")]),
        ("minimax-coding-plan", ROOT / "venvs/minimax-plan/Scripts/pythonw.exe", [launcher, "minimax-plan"]),
        ("minimax", ROOT / "venvs/minimax-mcp/Scripts/pythonw.exe", [launcher, "minimax"]),
    ]
    result = []
    for name, command, args in entries:
        if not Path(command).is_file() or not Path(args[0]).is_file():
            raise ValueError(f"Missing installed executable/script for {name}")
        # Exact blocked tools are not available to the model. Other tools retain
        # native task-scoped approval. Do not default to wildcard allow.
        policy = {"*": "ask"}
        if name == "Windows-MCP":
            policy.update({"PowerShell": "blocked", "Process": "blocked", "Registry": "blocked"})
        if name == "playwright":
            policy.update({"browser_run_code_unsafe": "blocked", "browser_install": "blocked"})
        result.append(
            {
                "name": name,
                "transport": "stdio",
                "command": str(command),
                "args": args,
                "cwd": str(workspace),
                "toolPolicy": policy,
            }
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--machine", action="store_true", help="Use the documented HKLM policy (administrator required)"
    )
    options = parser.parse_args()
    workspace = options.workspace.resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError("Workspace must be a directory")
    node = shutil.which("node.exe")
    if not node:
        raise ValueError("Node.js is required")
    servers = core_servers(workspace, node)
    policy_path = r"SOFTWARE\Policies\Claude"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, policy_path) as machine:
            if winreg.QueryInfoKey(machine)[1] and not options.machine:
                raise ValueError("Machine policy is present; per-user changes would be ignored. No changes made.")
    except FileNotFoundError:
        pass
    print(json.dumps({"workspace": str(workspace), "servers": [s["name"] for s in servers], "apply": options.apply}))
    if not options.apply:
        return
    config = Path(os.environ["LOCALAPPDATA"]) / "Claude-3p/claude_desktop_config.json"
    current = json.loads(config.read_text(encoding="utf-8-sig")) if config.exists() else {}
    if not isinstance(current, dict):
        raise ValueError("Existing client configuration is invalid; no changes made")
    backup = config.parent / "minimax-profile-backups" / uuid.uuid4().hex
    backup.mkdir(parents=True)
    if config.exists():
        shutil.copy2(config, backup / config.name)
    hive = winreg.HKEY_LOCAL_MACHINE if options.machine else winreg.HKEY_CURRENT_USER
    desired = {
        "managedMcpServers": json.dumps(servers),
        "mcpPersistentAlwaysAllowEnabled": "false",
        "mcpToolTimeoutSec": "180",
        "toolSearchEnabled": "false",
        "autoModeEnabled": "false",
        "builtinToolPolicy": json.dumps(
            {"Bash": "ask", "Write": "ask", "Edit": "ask", "REPL": "ask", "JavaScript": "ask"}
        ),
    }
    if options.machine:
        # Machine policy replaces, rather than merges, user policy. Copy only
        # reviewed connection/model fields when migrating an existing profile.
        # Preserve an existing machine connection. Migrate from HKCU only when
        # the machine value is absent; never silently restore a stale token.
        defaults = {
            "inferenceProvider": "gateway",
            "inferenceGatewayBaseUrl": "http://127.0.0.1:48217/anthropic",
            "inferenceGatewayAuthScheme": "x-api-key",
            "modelDiscoveryEnabled": "false",
            "inferenceModels": json.dumps([
                {"name": "claude-sonnet-4-5", "anthropicFamilyTier": "sonnet", "isFamilyDefault": True,
                 "supports1m": True, "labelOverride": "MiniMax M3"},
                {"name": "claude-opus-4-6", "anthropicFamilyTier": "opus", "isFamilyDefault": True,
                 "labelOverride": "MiniMax M2.7"},
                {"name": "claude-haiku-4-5", "anthropicFamilyTier": "haiku", "isFamilyDefault": True,
                 "labelOverride": "MiniMax M2.7 Highspeed"},
            ]),
        }
        for name in (*defaults, "inferenceGatewayApiKey"):
            for source_hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(source_hive, policy_path) as source_key:
                        desired[name] = winreg.QueryValueEx(source_key, name)[0]
                    break
                except FileNotFoundError:
                    continue
            else:
                if name == "inferenceGatewayApiKey":
                    from gateway_common import private_token
                    desired[name] = private_token()
                    if not desired[name]:
                        raise ValueError("Create the private local gateway token before applying the profile")
                else:
                    desired[name] = defaults[name]
        desired["disableWslSessions"] = "false"
    with winreg.CreateKey(hive, policy_path) as key:
        before = {}
        for name in desired:
            try:
                value, kind = winreg.QueryValueEx(key, name)
                before[name] = {"value": value, "kind": kind}
            except FileNotFoundError:
                before[name] = None
        atomic_json(backup / "managed-settings.json", before)
        # Preserve every non-MCP client preference. Save old optional servers as
        # a recoverable project profile instead of starting them at every launch.
        current["mcpServers"] = {}
        try:
            atomic_json(config, current)
            for name, value in desired.items():
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
        except BaseException:
            if (backup / config.name).exists():
                shutil.copy2(backup / config.name, config)
            for name, old in before.items():
                if old is not None:
                    winreg.SetValueEx(key, name, 0, old["kind"], old["value"])
                else:
                    try:
                        winreg.DeleteValue(key, name)
                    except FileNotFoundError:
                        pass
            raise
    print("Applied six core MCPs. Other client preferences preserved. Backup:", backup)


if __name__ == "__main__":
    main()
