"""Shared limits and secret loading. No shell, process control, or UI operations."""

import os
from pathlib import Path
import secrets
from contextlib import contextmanager
import http.client
import socket
import threading
import json
from urllib.parse import urlsplit

MAX_BODY_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_REQUESTS = 8
BODY_TIMEOUT = 10
UPSTREAM_TIMEOUT = 60
REQUEST_DEADLINE = 180


def strict_json(data):
    def invalid_constant(value):
        raise ValueError("non-finite JSON number")

    return json.loads(data, parse_constant=invalid_constant)


@contextmanager
def open_upstream(request):
    """No redirects, ambient proxy credentials, retries, or unbounded downloads.

    The caller supplies a fixed upstream URL, never a URL from a request body.
    The timer closes only this request's socket, including while reading headers.
    """
    url = urlsplit(request.full_url)
    if url.username or url.password or url.fragment:
        raise ValueError("invalid upstream URL")
    if url.scheme == "https":
        connection = http.client.HTTPSConnection(url.hostname, url.port, timeout=UPSTREAM_TIMEOUT)
    elif url.scheme == "http" and url.hostname == "127.0.0.1":
        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=UPSTREAM_TIMEOUT)
    else:
        raise ValueError("upstream must use HTTPS or IPv4 loopback")
    owned_socket = [None]
    expired = threading.Event()

    def expire():
        expired.set()
        sock = owned_socket[0] or connection.sock
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    timer = threading.Timer(REQUEST_DEADLINE, expire)
    timer.daemon = True
    timer.start()
    response = None
    try:
        connection.request(
            request.get_method(),
            url.path + ("?" + url.query if url.query else ""),
            body=request.data,
            headers=dict(request.header_items()),
        )
        owned_socket[0] = connection.sock
        if expired.is_set():
            raise TimeoutError("upstream deadline expired")
        response = connection.getresponse()
        yield response
        if expired.is_set():
            raise TimeoutError("upstream deadline expired")
    finally:
        timer.cancel()
        if response:
            response.close()
        connection.close()


def parse_dotenv(text):
    values = {}
    for raw in text.splitlines():
        line = raw.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if value:
            values[key.strip()] = value
    return values


def private_token():
    token = os.environ.get("MINIMAX_PROXY_TOKEN")
    if token is not None:
        token = token.strip()
        return token if len(token) >= 32 and not any(c.isspace() for c in token) else ""
    path = os.environ.get("MINIMAX_PROXY_TOKEN_FILE", r"C:\private\.proxy-token")
    try:
        token = Path(path).read_text(encoding="utf-8-sig").strip()
        return token if len(token) >= 32 and not any(c.isspace() for c in token) else ""
    except (OSError, UnicodeError):
        return ""


def authorized(headers):
    expected = private_token()
    if not expected:
        return False
    provided = headers.get("X-Proxy-Token") or headers.get("X-Api-Key") or ""
    if not provided:
        auth = headers.get("Authorization", "")
        scheme, _, value = auth.partition(" ")
        if scheme.lower() == "bearer":
            provided = value.strip()
    return secrets.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


_job_handle = None


def install_process_limits():
    """Windows Job: one process, 256 MiB, 20% CPU, no desktop/clipboard changes.

    Fail closed if Windows cannot install these limits. Call only at startup,
    never while importing a module into another application's process.
    """
    global _job_handle
    if os.name != "nt" or _job_handle:
        return
    import ctypes as c
    from ctypes import wintypes as w

    class Basic(c.Structure):
        _fields_ = [
            ("per_process", c.c_int64),
            ("per_job", c.c_int64),
            ("flags", w.DWORD),
            ("min_ws", c.c_size_t),
            ("max_ws", c.c_size_t),
            ("process_limit", w.DWORD),
            ("affinity", c.c_size_t),
            ("priority", w.DWORD),
            ("scheduling", w.DWORD),
        ]

    class IO(c.Structure):
        _fields_ = [
            (name, c.c_uint64)
            for name in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")
        ]

    class Extended(c.Structure):
        _fields_ = [
            ("basic", Basic),
            ("io", IO),
            ("process_memory", c.c_size_t),
            ("job_memory", c.c_size_t),
            ("peak_process", c.c_size_t),
            ("peak_job", c.c_size_t),
        ]

    class Cpu(c.Structure):
        _fields_ = [("flags", w.DWORD), ("rate", w.DWORD)]

    kernel = c.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
    kernel.SetInformationJobObject.restype = w.BOOL
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.AssignProcessToJobObject.restype = w.BOOL
    kernel.CloseHandle.argtypes = [w.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise c.WinError(c.get_last_error())
    limits = Extended()
    limits.basic.flags = 0x8 | 0x100 | 0x2000  # active count, process memory, kill on close
    limits.basic.process_limit = 1
    limits.process_memory = 256 * 1024 * 1024
    ui = w.DWORD(0xFF)
    cpu = Cpu(0x1 | 0x4, 2000)  # enabled, hard cap; hundredths of a percent
    try:
        for kind, value in ((9, limits), (4, ui), (15, cpu)):
            if not kernel.SetInformationJobObject(job, kind, c.byref(value), c.sizeof(value)):
                raise c.WinError(c.get_last_error())
        if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
            raise c.WinError(c.get_last_error())
    except BaseException:
        kernel.CloseHandle(job)
        raise
    _job_handle = job
