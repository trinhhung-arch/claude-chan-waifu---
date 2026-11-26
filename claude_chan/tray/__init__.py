"""Icon ở khay hệ thống. build(items) -> (icon, todo): pystray gọi menu từ luồng riêng của nó, nên mỗi mục chỉ xếp
việc vào todo; luồng giao diện lấy ra làm (run_pending)."""
import queue

import pystray
from PIL import Image

from ..core.config import EMOTE_DIR, TITLE

SEPARATOR = pystray.Menu.SEPARATOR


def build(items):
    """items: các bộ (chữ hoặc hàm(_)->chữ, việc, {checked=..., default=...}) hoặc SEPARATOR."""
    todo = queue.Queue()
    queued = lambda job: lambda: todo.put(job)  # pystray chỉ nhận hàm 0-2 tham số
    menu = [it if it is SEPARATOR else pystray.MenuItem(it[0], queued(it[1]), **(it[2] if len(it) > 2 else {}))
            for it in items]
    icon = pystray.Icon("tro_ly_man_hinh", Image.open(EMOTE_DIR / "mim_cuoi.png").resize((64, 64)), TITLE, pystray.Menu(*menu))
    return icon, todo


def run_pending(todo):
    while not todo.empty():
        todo.get()()
