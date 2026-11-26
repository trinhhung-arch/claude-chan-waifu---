"""Nhìn màn hình: chụp, so xem có đổi không, nhận ra cửa sổ riêng tư không được chụp."""
import io

import mss
import numpy as np
from PIL import Image, ImageChops
from scipy.signal import fftconvolve

from ..core.config import PRIVATE_WORDS


def screenshot():
    with mss.MSS() as s:
        shot = s.grab(s.monitors[1])  # màn hình chính
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    img.thumbnail((1024, 1024))  # đủ để model đọc chữ mà ảnh vẫn nhẹ (~150KB)
    return img  # chỉ nằm trong RAM, không ghi ra đĩa


def grab_screen():
    """Ảnh nguyên cỡ màn hình chính (chỉ trong RAM) + toạ độ góc trên trái của nó trên desktop.
    shortcut: chỉ màn hình chính; dùng nhiều màn hình thì chụp cả màn hình phụ."""
    with mss.MSS() as s:
        m = s.monitors[1]
        shot = s.grab(m)
    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX"), m["left"], m["top"]


def locate(full, part, k=4):
    """part (ảnh cắt từ full, vd vùng người dùng vừa chụp màn hình) nằm ở đâu trong full -> (x, y) góc trên trái, hoặc
    None nếu không khớp chỗ nào. So ảnh xám thu nhỏ k lần bằng tổng bình phương sai khác, tính nhanh qua FFT."""
    F = np.asarray(full.convert("L").resize((full.width // k, full.height // k)), float)
    T = np.asarray(part.convert("L").resize((max(1, part.width // k), max(1, part.height // k))), float)
    th, tw = T.shape
    if th > F.shape[0] or tw > F.shape[1]:
        return None
    corr = fftconvolve(F, T[::-1, ::-1], mode="valid")
    c = np.pad(F ** 2, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    window = c[th:, tw:] - c[:-th, tw:] - c[th:, :-tw] + c[:-th, :-tw]  # tổng bình phương từng ô cỡ T
    ssd = window - 2 * corr + (T ** 2).sum()
    y, x = np.unravel_index(np.argmin(ssd), ssd.shape)
    return (int(x) * k, int(y) * k) if ssd[y, x] / T.size < 300 else None


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


def is_private(title):
    title = title.lower()
    return any(w in title for w in PRIVATE_WORDS)
