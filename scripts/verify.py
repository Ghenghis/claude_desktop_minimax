"""One-pass source verification. Never traverse dependencies or user projects."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    requested = [Path(p).resolve() for p in sys.argv[1:] if p != '--strict']
    files = requested or sorted({*ROOT.glob('*.py'), *(ROOT/'scripts').glob('*.py'), *(ROOT/'tests').glob('*.py')})
    for path in files:
        if not path.is_relative_to(ROOT) or path.suffix != '.py' or not path.is_file():
            raise ValueError('Verifier accepts existing Python source files inside this repository only')
        compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec')
    result = subprocess.run([sys.executable, '-m', 'flake8', *map(str, files)], cwd=ROOT,
                            timeout=60, creationflags=0x08000000 if sys.platform == 'win32' else 0)
    print(f'Verified {len(files)} source files; no dependency directories scanned.')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
