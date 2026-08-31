# Claude Desktop acceptance task

Open a new **Code** task in a new disposable folder under the configured
workspace root (on this host, C:\Users\Admin\projects). Do not reuse a folder
containing your work. Use the normal permission mode. Paste the text
below. This is a manual test, never a scheduled task or a self-repair routine.

## Prompt to paste

Run an acceptance test in this scratch project only. Do not change settings,
install software, stop processes, restart services, change permissions, inspect
credentials, or modify any other project. Do not fix missing tools by installing
anything. Report blocked or failed steps honestly. Do not invent results.

1. List the actual available MCP server and tool names. Identify Windows-MCP,
   project-files, playwright, context7, minimax-coding-plan, and minimax.
2. Call Windows-MCP Snapshot with use_vision=false and use_ui_tree=false. This
   checks Windows integration without sending screenshots of unrelated work.
   Do not click or type in other applications.
3. Use project-files to create acceptance-note.txt containing exactly
   CLAUDE_FILE_TEST_PASSED, then read it back. Stay inside this workspace.
4. Create add.py with an add(a,b) function and test_add.py with meaningful tests
   for positive, negative, and zero inputs. Run these tests using the native
   terminal tool. Do not install dependencies. Report the actual exit status.
5. Use Playwright's isolated browser to navigate to https://example.com, verify
   the Example Domain heading, and close only that isolated browser.
6. Use Context7 resolve-library-id for Python pathlib. Use MiniMax coding-plan
   web_search for the official Python pathlib documentation. Call MiniMax
   list_voices with voice_type=system. No media generation, uploads, or cloning.
7. Use the native terminal's existing OpenSSH client for this read-only command:
   ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=8 daveai "uname -s; id -un"
   If the alias is not configured or host verification fails, stop this step.
   Do not disable host verification. Do not write anything to the VPS. Report
   whether the existing account is root; do not grant unattended root access.
8. Write acceptance-results.md listing PASS, FAIL, or BLOCKED for every step,
   exact tools used, and concise observed evidence. Never claim all tools or
   all projects are tested by this sample. No loops after this task completes.

## Windows input extension

For a deliberate UI input test, explicitly launch
`pwsh -NoProfile -File scripts/Start-WindowsTestFixture.ps1`.
It creates one disposable WinForms window titled **Claude MCP test fixture**.
Tell Claude to use Snapshot (use_vision=false, use_ui_tree=true), InspectWindow,
WindowSetValue and WindowInvoke only in that window: set the uniquely named
Acceptance input field to CLAUDE_WINDOWS_TEST_PASSED, invoke Verify test input,
and use InspectWindow to observe the matching result label. Supply the exact
observed window_handle, window_title and control_name for each action.
The pinned upstream server skips window enumeration when use_ui_tree=false;
that fast metadata-only call cannot locate the fixture.
Never use the user's Notepad documents as a test surface. Stop if the fixture
is not visible; never guess coordinates or substitute another application.
InspectWindow takes the exact observed handle and title and reads only that
window's accessibility tree. It does not raise the global element budget or
change focus. Re-check coordinates if a window moves or becomes covered.
WindowClick/WindowType require that same exact handle and title plus observed x/y
coordinates. They verify normal foreground focus and that another window does
not cover the point; failures send no input. They never attach application input
threads. Run UI operations sequentially and do not change focus during typing.
This is a safety check, not an operating-system sandbox or an atomic input lease.
WindowSetValue/WindowInvoke use supported accessibility patterns instead of
global input. They reject ambiguous names, password fields, unsupported controls,
and incomplete searches. They do not require or force foreground focus.

## Scope

OpenSSH and native Claude Code file/terminal tools provide coding and VPS access.
An additional unrestricted root SSH MCP would duplicate that capability and
increase risk. Unity, IDA and database tools require their actual project/editor
or target connection; enable and test each separately for the project that needs
it. A missing editor or login must be reported, never silently bypassed.
