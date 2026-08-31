"""Validate OS limits in a disposable child, never the test runner or user's apps."""

import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "nt", "Windows Job Object acceptance test")
class ProcessLimits(unittest.TestCase):
    def test_gateway_cannot_create_child_process(self):
        script = """
from gateway_common import install_process_limits
install_process_limits()
import subprocess, sys
try:
    child = subprocess.Popen([sys.executable, '-c', 'pass'], creationflags=subprocess.CREATE_NO_WINDOW)
except OSError as error:
    print('blocked', error.winerror)
else:
    child.wait(timeout=5)
    raise AssertionError('gateway was allowed to create a child')
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("blocked 1816", result.stdout)  # ERROR_NOT_ENOUGH_QUOTA from the job's process limit

    def test_memory_limit_is_enforced_without_harming_parent(self):
        script = """
from gateway_common import install_process_limits
install_process_limits()
try:
    allocation = bytearray(320 * 1024 * 1024)
except MemoryError:
    print('allocation denied')
else:
    raise AssertionError('allocation exceeded the limit')
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("allocation denied", result.stdout)


if __name__ == "__main__":
    unittest.main()
