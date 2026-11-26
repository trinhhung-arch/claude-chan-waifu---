"""vision: chụp màn hình ra JPEG, màn hình đổi hay không, cửa sổ riêng tư."""
from PIL import Image, ImageDraw

from claude_chan.vision import changed, is_private, screenshot, to_jpeg

assert to_jpeg(screenshot())[:2] == b"\xff\xd8"  # ra đúng JPEG

page = Image.new("RGB", (1024, 576), "white")
ImageDraw.Draw(page).rectangle((0, 0, 1024, 40), fill="navy")
same = page.copy()
typed = page.copy()
ImageDraw.Draw(typed).text((100, 300), "vài chữ mới gõ", fill="black")  # gõ thêm vài chữ: coi như không đổi
other = Image.new("RGB", (1024, 576), "black")  # chuyển sang cửa sổ khác
scrolled = Image.new("RGB", (1024, 576), "white")
ImageDraw.Draw(scrolled).rectangle((0, 200, 1024, 240), fill="navy")  # cuộn trang
assert changed(page, None)  # lần đầu luôn gửi
assert not changed(same, page) and not changed(typed, page)
assert changed(other, page) and changed(scrolled, page)

assert is_private("Vietcombank - Ngân hàng số - Google Chrome")
assert is_private("Đăng nhập - Facebook") and is_private("Trang mới - [InPrivate] - Microsoft Edge")
assert is_private("Sign in - Google Accounts") and is_private("Bitwarden")
assert not is_private("assistant.py - Visual Studio Code") and not is_private("YouTube - Google Chrome")

# dò vị trí ảnh cắt trong ảnh màn hình (để biết ảnh người dùng chụp có lọt Claude-chan không)
import numpy as np
from PIL import Image
from claude_chan.vision import locate
rng = np.random.default_rng(3)
screen = Image.fromarray(rng.integers(0, 255, (540, 960, 3), dtype=np.uint8))
screen = screen.resize((1920, 1080), Image.NEAREST)  # khối 2x2 như chữ / ảnh thật, không phải nhiễu từng pixel
for box in ((300, 200, 700, 500), (0, 0, 1920, 1080), (1500, 820, 1900, 1070)):
    x, y = locate(screen, screen.crop(box))
    assert abs(x - box[0]) <= 4 and abs(y - box[1]) <= 4, (box, x, y)
assert locate(screen, Image.new("RGB", (300, 200), "red")) is None  # ảnh không có trên màn hình
