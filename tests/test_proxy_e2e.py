"""Compatibility entry point: real network contracts replaced shape-only checks."""

from pathlib import Path
import unittest

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
