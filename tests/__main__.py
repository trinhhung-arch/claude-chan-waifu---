"""Chạy mọi test: py -m tests   (mỗi file test là assert ở cấp module, import là chạy)."""
import importlib
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
for path in sorted(Path(__file__).parent.glob("test_*.py")):
    importlib.import_module(f"tests.{path.stem}")
    print("ok", path.stem)
print("ok")
