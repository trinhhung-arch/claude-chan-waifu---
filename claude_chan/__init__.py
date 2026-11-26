"""Claude-chan: nhân vật trợ lý màn hình (modular monolith).

Mỗi thư mục con là một module, chỉ dùng nhau qua những gì xuất ra ở __init__.py của nó; file bắt đầu bằng "_" là
nội bộ, module khác không được import. core ← dialogue, memory, desktop, vision ← brain, character ← wellbeing,
focus, behaviors, tray, settings ← app (nối mọi thứ). tests/test_boundaries.py kiểm tra các quy tắc này.
"""
