"""Window-specific tools for the pinned Windows-MCP runtime; no supervisor."""

from typing import Literal
from time import monotonic


def validate_window(native, handle, title):
    if isinstance(handle, bool) or not isinstance(handle, int) or handle <= 0:
        raise ValueError("Use a positive handle from a current Snapshot")
    if not isinstance(title, str) or not title or len(title) > 512:
        raise ValueError("An exact, observed window title is required")
    if not native.IsWindow(handle) or native.GetWindowText(handle) != title:
        raise ValueError("Window handle/title changed; obtain a new Snapshot")


def focus_window(native, handle, title):
    validate_window(native, handle, title)
    if not native.IsWindowVisible(handle) or native.IsIconic(handle):
        raise ValueError("Target is hidden or minimized; restore it manually")
    if native.GetForegroundWindow() != handle:
        # Normal OS request only. Never attach input queues, send synthetic Alt,
        # resize windows, change desktop, or bypass Windows focus restrictions.
        try:
            native.SetForegroundWindow(handle)
        except Exception as error:
            raise ValueError("Windows refused focus; focus the intended window manually") from error
    if native.GetForegroundWindow() != handle:
        raise ValueError("Target did not receive focus; no input sent")
    validate_window(native, handle, title)


def guarded_point(native, handle, title, x, y):
    if any(isinstance(n, bool) or not isinstance(n, int) for n in (x, y)):
        raise ValueError("Coordinates must be integers from a current inspection")
    focus_window(native, handle, title)
    left, top, right, bottom = native.GetWindowRect(handle)
    if not (left <= x < right and top <= y < bottom):
        raise ValueError("Point is outside the intended window")
    hit = native.WindowFromPoint((x, y))
    if native.GetAncestor(hit, 2) != handle:
        raise ValueError("Another window covers the target point; no input sent")
    if native.GetForegroundWindow() != handle:
        raise ValueError("Focus changed; no input sent")
    return (x, y)


def inspect_window(desktop, native, window_handle, window_title):
    # A stale/reused handle must never select another application's window.
    validate_window(native, window_handle, window_title)
    # Do not focus, activate, restore, launch, resize, attach threads, or input.
    # Upstream applies its 500-element budget to this one explicit window.
    state = desktop.tree.get_state(window_handle, [], use_dom=False)
    if native.GetWindowText(window_handle) != window_title:
        raise ValueError("Window changed during inspection; discard these coordinates")
    if not state.status:
        raise ValueError("Window accessibility inspection failed")
    result = state.semantic_tree_to_string() + "\n" + state.interactive_elements_to_string()
    if len(result) > 100_000:
        raise ValueError("Window inspection exceeded the text limit")
    return result


def find_control(native, uia, handle, title, name, kind):
    """Resolve one control inside one window; never search the whole desktop."""
    validate_window(native, handle, title)
    if not isinstance(name, str) or not name or len(name) > 512:
        raise ValueError("An exact observed control name is required")
    if not native.IsWindowVisible(handle) or native.IsIconic(handle):
        raise ValueError("Target is hidden or minimized")
    root = uia.ControlFromHandle(handle)
    matches = []
    deadline = monotonic() + 5
    for count, (control, _) in enumerate(uia.WalkControl(root, includeTop=False, maxDepth=12)):
        if count >= 500 or monotonic() > deadline:
            raise ValueError("Control search budget exceeded; no action taken")
        if control.ControlTypeName == kind and control.Name == name:
            matches.append(control)
    if len(matches) != 1:
        raise ValueError("Control name/type must identify exactly one element; no action taken")
    control = matches[0]
    validate_window(native, handle, title)
    top = control.GetTopLevelControl()
    if top is None or top.NativeWindowHandle != handle or control.Name != name:
        raise ValueError("Control/window identity changed; no action taken")
    if not control.IsEnabled or control.IsOffscreen or control.IsPassword:
        raise ValueError("Control is disabled, offscreen or a password field")
    return control


def read_window_labels(native, uia, handle, title):
    """Include static status/error labels omitted by upstream's interactive tree."""
    validate_window(native, handle, title)
    root = uia.ControlFromHandle(handle)
    labels = []
    deadline = monotonic() + 5
    for count, (control, _) in enumerate(uia.WalkControl(root, includeTop=False, maxDepth=12)):
        if count >= 500 or monotonic() > deadline:
            labels.append("[Static label listing truncated at the inspection budget]")
            break
        if control.ControlTypeName == "TextControl" and not control.IsOffscreen:
            name = control.Name
            if name:
                labels.append(name[:1000])
    validate_window(native, handle, title)
    result = "\n".join(labels)
    if len(result) > 100_000:
        raise ValueError("Static label text exceeded the inspection limit")
    return result


def register_window_inspection(server, get_desktop):
    import win32gui

    @server.tool(
        name="InspectWindow",
        description=(
            "Read the accessibility tree of ONE existing window using its exact title and handle from Snapshot. "
            "Returns actual screen coordinates while preserving the 500-element limit. Use when the whole-desktop "
            "Snapshot omits a background window. Does not change focus, input, launch, close or alter any window."
        ),
        annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    )
    def inspect(window_handle: int, window_title: str) -> str:
        import windows_mcp.uia as uia

        with uia.UIAutomationInitializerInThread():
            result = inspect_window(get_desktop(), win32gui, window_handle, window_title)
            labels = read_window_labels(win32gui, uia, window_handle, window_title)
        result += "\nVisible static labels:\n" + (labels or "[None exposed by this window]")
        if len(result) > 100_000:
            raise ValueError("Combined window inspection exceeded the text limit")
        return result

    @server.tool(name="WindowSetValue", description=(
        "Set the complete value of ONE uniquely named Edit control observed by InspectWindow in an exact window. "
        "Uses accessibility ValuePattern, without focusing, clicking, clipboard or global keystrokes. "
        "Replaces existing text; at most 2048 characters. Fails for ambiguous names, password/read-only fields "
        "or unsupported controls. Prefer this over WindowType when available."
    ))
    def set_value(window_handle: int, window_title: str, control_name: str, value: str) -> str:
        import windows_mcp.uia as uia

        if len(value) > 2048:
            raise ValueError("Value exceeds the per-call limit")
        with uia.UIAutomationInitializerInThread():
            control = find_control(win32gui, uia, window_handle, window_title, control_name, "EditControl")
            pattern = control.GetValuePattern()
            if pattern is None or pattern.IsReadOnly:
                raise ValueError("Control does not support editable ValuePattern")
            validate_window(win32gui, window_handle, window_title)
            if not pattern.SetValue(value, waitTime=0):
                raise ValueError("Control did not accept SetValue; inspect before any further action")
            if pattern.Value != value:
                raise ValueError("Value read-back did not match; inspect before any further action")
        return "Exact text field accepted the value; read-back matched"

    @server.tool(name="WindowInvoke", description=(
        "Invoke ONE uniquely named Button control observed by InspectWindow in an exact window. "
        "Uses accessibility InvokePattern, without focus changes, global input or coordinate guessing. "
        "Fails for ambiguous names or unsupported controls. The button's action still needs user approval."
    ))
    def invoke(window_handle: int, window_title: str, control_name: str) -> str:
        import windows_mcp.uia as uia

        with uia.UIAutomationInitializerInThread():
            control = find_control(win32gui, uia, window_handle, window_title, control_name, "ButtonControl")
            pattern = control.GetInvokePattern()
            if pattern is None:
                raise ValueError("Control does not support InvokePattern")
            validate_window(win32gui, window_handle, window_title)
            if not pattern.Invoke(waitTime=0):
                raise ValueError("Invoke did not report success; inspect before any further action")
        return "Exact button invoked; inspect the resulting window state"

    @server.tool(name="WindowClick", description=(
        "Click coordinates observed inside one exact window. Rechecks title, foreground and point visibility. "
        "Does not launch or resize windows and never attaches application input threads. "
        "Fails if Windows refuses focus."
    ))
    def click(window_handle: int, window_title: str, x: int, y: int,
              button: Literal["left", "right", "middle"] = "left", clicks: Literal[1, 2] = 1) -> str:
        point = guarded_point(win32gui, window_handle, window_title, x, y)
        get_desktop().click(point, button=button, clicks=clicks)
        return "Click sent to the verified window point"

    @server.tool(name="WindowType", description=(
        "Type at an observed text-field coordinate in one exact window, after title/focus/visibility checks. "
        "At most 2048 characters. Never use a terminal or security prompt to bypass permissions."
    ))
    def type_text(window_handle: int, window_title: str, x: int, y: int, text: str,
                  clear: bool = False, press_enter: bool = False) -> str:
        if len(text) > 2048:
            raise ValueError("Text exceeds the per-call limit; use project file tools for large edits")
        point = guarded_point(win32gui, window_handle, window_title, x, y)
        get_desktop().type(point, text, clear=clear, press_enter=press_enter)
        return "Text sent to the verified window field"

    @server.tool(name="WindowScroll", description="Scroll a verified point inside one exact visible window.")
    def scroll(window_handle: int, window_title: str, x: int, y: int,
               direction: Literal["up", "down", "left", "right"] = "down", amount: int = 1) -> str:
        if not 1 <= amount <= 10:
            raise ValueError("Scroll amount must be 1 through 10")
        point = guarded_point(win32gui, window_handle, window_title, x, y)
        kind = "vertical" if direction in ("up", "down") else "horizontal"
        get_desktop().scroll(point, type=kind, direction=direction, wheel_times=amount)
        return "Scrolled the verified window"

    @server.tool(name="WindowMove", description="Move the pointer to an observed point inside one verified window.")
    def move(window_handle: int, window_title: str, x: int, y: int) -> str:
        point = guarded_point(win32gui, window_handle, window_title, x, y)
        get_desktop().move(point)
        return "Pointer moved inside the verified window"

    @server.tool(name="WindowShortcut", description=(
        "Send a common editing shortcut in one exact foreground window. No task-manager, Run, desktop-switch "
        "or application-close shortcuts. Use native coding tools for shell commands."
    ))
    def shortcut(window_handle: int, window_title: str, keys: str) -> str:
        allowed = {"ctrl+a", "ctrl+c", "ctrl+v", "ctrl+x", "ctrl+z", "ctrl+y", "ctrl+s", "ctrl+f",
                   "ctrl+shift+z", "enter", "escape", "tab", "shift+tab", "home", "end",
                   "ctrl+home", "ctrl+end", "left", "right", "up", "down", "backspace", "delete"}
        if keys.lower() not in allowed:
            raise ValueError("Shortcut is outside the reviewed editing set")
        focus_window(win32gui, window_handle, window_title)
        get_desktop().shortcut(keys)
        return "Editing shortcut sent to the verified window"
