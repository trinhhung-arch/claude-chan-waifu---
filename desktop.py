"""Đọc từ Windows: chụp màn hình, cửa sổ đang mở, rời máy bao lâu, pin, mạng, toàn màn hình."""
import ctypes
import io

import mss
from PIL import Image, ImageChops

from config import PRIVATE_WORDS

def screenshot():
    with mss.MSS() as s:
        shot = s.grab(s.monitors[1])  # màn hình chính
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    img.thumbnail((1024, 1024))  # đủ để model đọc chữ mà ảnh vẫn nhẹ (~150KB)
    return img  # chỉ nằm trong RAM, không ghi ra đĩa


def to_jpeg(img):
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return buf.getvalue()


def changed(img, last):
    """Màn hình có đổi đáng kể so với ảnh đã gửi lần trước không: so lưới xám 64x36, >5% ô đổi rõ thì tính là đổi.
    shortcut: nhân vật và bong bóng nằm trong ảnh nên cũng góp vài % thay đổi; nếu bỏ sót/nhạy quá thì che vùng cửa sổ nhân vật."""
    if last is None:
        return True
    a, b = (im.convert("L").resize((64, 36)) for im in (img, last))
    diff = ImageChops.difference(a, b).point(lambda v: 255 if v > 25 else 0)
    return diff.histogram()[255] > 0.05 * 64 * 36


def active_title():
    u = ctypes.windll.user32
    u.GetForegroundWindow.restype = ctypes.c_void_p
    buf = ctypes.create_unicode_buffer(512)
    u.GetWindowTextW(ctypes.c_void_p(u.GetForegroundWindow()), buf, 512)
    return buf.value


def idle_seconds():
    """Số giây từ lần cuối người dùng chạm chuột hoặc bàn phím (Windows tự đếm)."""
    class LastInput(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    info = LastInput(ctypes.sizeof(LastInput))
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
    return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000  # & : bộ đếm quay vòng sau 49 ngày


def battery():
    """(phần trăm pin, đang cắm sạc); máy bàn / không đọc được thì (None, True)."""
    class PowerStatus(ctypes.Structure):
        _fields_ = [("ac", ctypes.c_ubyte), ("flag", ctypes.c_ubyte), ("percent", ctypes.c_ubyte),
                    ("saver", ctypes.c_ubyte), ("life", ctypes.c_ulong), ("full", ctypes.c_ulong)]
    s = PowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)) or s.percent == 255 or s.flag & 128:
        return None, True  # 255 = không rõ, flag 128 = không có pin
    return s.percent, s.ac == 1


def online():
    """Windows có đang báo có mạng không (chỉ hỏi Windows, không gửi gì ra ngoài)."""
    flags = ctypes.c_ulong()
    return bool(ctypes.windll.wininet.InternetGetConnectedState(ctypes.byref(flags), 0))


def is_private(title):
    title = title.lower()
    return any(w in title for w in PRIVATE_WORDS)


def fullscreen():
    """Cửa sổ phía trước phủ kín màn hình (game, video toàn màn hình), không tính màn hình nền desktop."""
    u = ctypes.windll.user32
    u.GetForegroundWindow.restype = ctypes.c_void_p
    h = ctypes.c_void_p(u.GetForegroundWindow())
    cls = ctypes.create_unicode_buffer(64)
    u.GetClassNameW(h, cls, 64)
    r = (ctypes.c_long * 4)()
    if cls.value in ("Progman", "WorkerW") or not u.GetWindowRect(h, r):
        return False
    return r[0] <= 0 and r[1] <= 0 and r[2] >= u.GetSystemMetrics(0) and r[3] >= u.GetSystemMetrics(1)
