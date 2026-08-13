#!/usr/bin/env bash
# Project verifier — run after any Edit or Write to a .py file.
# Returns 0 if everything is clean, non-zero if anything fails.
#
# Usage:
#   bash .claude/verifiers/run.sh                  # verify all .py files
#   bash .claude/verifiers/run.sh <file.py>        # verify one file
#   bash .claude/verifiers/run.sh --strict         # treat warnings as errors

set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STRICT=0
TARGET=""

for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    -h|--help)
      echo "Usage: run.sh [--strict] [<file.py>]"
      exit 0
      ;;
    *) TARGET="$arg" ;;
  esac
done

if [ -z "$TARGET" ]; then
  TARGET=$(find "$ROOT" -name "*.py" -not -path "*/__pycache__/*" -not -path "*/.venv/*" | tr '\n' ' ')
fi

fail=0
for f in $TARGET; do
  [ -f "$f" ] || continue
  echo "[verify] py_compile $f"
  python -m py_compile "$f" || { fail=1; echo "[verify] FAIL: $f"; continue; }

  if command -v flake8 >/dev/null 2>&1; then
    echo "[verify] flake8 $f"
    flake8_args=( --max-line-length=120 )
    if [ "$STRICT" = "1" ]; then
      flake8_args+=( --select=E9,F63,F7,F82 --show-source --statistics )
    fi
    flake8 "${flake8_args[@]}" "$f" || fail=1
  else
    echo "[verify] flake8 not installed; skipping (pip install flake8)"
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "[verify] FAILED"
  exit 1
fi
echo "[verify] OK"
exit 0