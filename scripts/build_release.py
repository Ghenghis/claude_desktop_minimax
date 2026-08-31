"""Build a source-only archive from the reviewed allowlist; never copy a tree."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    entries = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
    if len(entries) != len(set(entries)):
        raise ValueError("Duplicate archive path")
    reviewed = []
    for relative in entries:
        path = root / relative
        resolved = path.resolve(strict=True)
        if (Path(relative).is_absolute() or ".." in Path(relative).parts or not resolved.is_relative_to(root)
                or path.is_symlink() or not resolved.is_file() or resolved.stat().st_size > 5_000_000):
            raise ValueError("Invalid release allowlist path")
        data = resolved.read_bytes()
        reviewed.append((relative, data))
    options.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: never overwrite a user's archive or follow a symlink.
    with options.output.open("xb") as target:
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for relative, data in reviewed:
                archive.writestr(relative, data)
    with zipfile.ZipFile(options.output) as archive:
        if archive.testzip() is not None or sorted(archive.namelist()) != sorted(entries):
            raise RuntimeError("Archive verification failed")
    digest = hashlib.sha256(options.output.read_bytes()).hexdigest()
    print(json.dumps({"path": str(options.output.resolve()), "files": len(entries), "sha256": digest}))


if __name__ == "__main__":
    main()
