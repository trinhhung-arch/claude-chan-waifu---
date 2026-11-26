"""Ranh giới module (xem claude_chan/__init__.py): chỉ import module ở tầng thấp hơn, và chỉ qua __init__ của nó —
file "_xxx" là nội bộ, module khác không được đụng."""
import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "claude_chan"
LAYER = {"core": 0, "dialogue": 1, "memory": 1, "desktop": 1, "vision": 1, "brain": 2, "character": 2,
         "wellbeing": 3, "focus": 3, "behaviors": 3, "tray": 3, "settings": 3, "game": 3, "app": 4}


def imports(path):
    """(module đích, có đụng file nội bộ không) cho mỗi import trỏ tới module khác trong claude_chan."""
    rel = path.relative_to(PKG).with_suffix("").parts  # ("brain", "_loop") hoặc ("app",)
    here = rel[:-1] if len(rel) > 1 else ()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            if node.level:  # import tương đối: tính ra đường dẫn tuyệt đối trong gói
                base = list(here[:len(here) - node.level + 1]) if node.level <= len(here) + 1 else None
                assert base is not None, (path, node.module)
                parts = base + (node.module.split(".") if node.module else [])
            elif node.module and node.module.startswith("claude_chan"):
                parts = node.module.split(".")[1:]
            else:
                continue
            if not parts:  # "from . import brain, tray" ở gốc gói: mỗi tên là một module
                yield from ((a.name, False) for a in node.names)
            else:
                yield parts[0], any(p.startswith("_") for p in parts[1:])
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("claude_chan."):
                    parts = a.name.split(".")[1:]
                    yield parts[0], any(p.startswith("_") for p in parts[1:])


files = [p for p in PKG.rglob("*.py") if "__pycache__" not in p.parts and p.parent != PKG or p.name == "app.py"]
assert {p.relative_to(PKG).parts[0].removesuffix(".py") for p in files} == set(LAYER), "module mới: thêm vào LAYER"
for path in files:
    me = path.relative_to(PKG).parts[0].removesuffix(".py")
    for target, private in imports(path):
        if target == me:
            continue
        assert target in LAYER, (path, target)
        assert LAYER[target] < LAYER[me], f"{path.relative_to(PKG)}: {me} (tầng {LAYER[me]}) không được import {target}"
        assert not private, f"{path.relative_to(PKG)}: import file nội bộ của {target}, dùng __init__ của nó"

# những gì nằm ngoài gói (assistant.py, tests) cũng chỉ dùng cửa công khai
for path in [PKG.parent / "assistant.py", *Path(__file__).parent.glob("test_*.py")]:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("claude_chan"):
            assert not any(p.startswith("_") for p in node.module.split(".")), (path.name, node.module)
