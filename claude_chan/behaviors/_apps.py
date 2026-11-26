"""Nhận ra người dùng đang mở loại app nào (code / game / chat) từ tiêu đề cửa sổ."""
from ..core.config import APPS


def app_category(title, is_fullscreen=False):
    """Loại app đang mở theo tiêu đề cửa sổ ("code" / "game" / "chat"), không nhận ra thì None.
    Cửa sổ toàn màn hình mà không phải trình duyệt (video YouTube...) thì coi là đang chơi game."""
    t = title.lower()
    for cat, words in APPS.items():
        if any(w in t for w in words):
            return cat
    if is_fullscreen and title and not any(b in t for b in ("chrome", "edge", "firefox", "opera", "brave", "cốc cốc")):
        return "game"
    return None
