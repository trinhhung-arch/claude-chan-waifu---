"""Dựng ảnh cho cửa sổ màu khoá (emote có khung thở, ký hiệu bay, ba chấm đang nghĩ) và cửa sổ phủ trong suốt."""
import ctypes
import functools
import tkinter as tk

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk

from ..core.config import EMOTE_DIR, EMOTES, KEY, ROOT, SIZE

BREATH = 5  # thở: thân cao thêm tối đa 5px (~2%), đáy giữ nguyên
HEART_IMG = Image.open(ROOT / "tim_pixel.png").convert("RGBA")  # tim pixel bay ra khi được xoa đầu


def keyed(im):
    """Ảnh RGBA -> PhotoImage trên nền màu khoá. Màu khoá chỉ trong suốt 0/1: cắt alpha ở 50% để mép không bị viền
    hồng của KEY."""
    bg = Image.new("RGBA", im.size, KEY)
    bg.paste(im, mask=im.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
    return ImageTk.PhotoImage(bg.convert("RGB"))


def emote_frames():
    """(tên emote, lật?) -> [khung cao SIZE, SIZE+1, ..., SIZE+BREATH]."""
    pics = {}
    for name in EMOTES:
        base = Image.open(EMOTE_DIR / f"{name}.png").convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
        for flip in (False, True):
            src = ImageOps.mirror(base) if flip else base
            pics[name, flip] = [keyed(src.resize((SIZE, SIZE + k), Image.BICUBIC)) for k in range(BREATH + 1)]
    return pics


@functools.lru_cache(maxsize=None)
def _base(name):
    return Image.open(EMOTE_DIR / f"{name}.png").convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)


@functools.lru_cache(maxsize=None)
def squash_frame(name, flip, sx, sy):
    """Ảnh emote bẹp / giãn (ngang sx, dọc sy lần), dựng lúc cần rồi giữ lại: đáp xuống thì bẹp rồi bật lại."""
    im = _base(name).resize((round(SIZE * sx), round(SIZE * sy)), Image.BICUBIC)
    return keyed(ImageOps.mirror(im) if flip else im)


@functools.lru_cache(maxsize=None)
def peek_frame(name, angle):
    """Ảnh emote xoay để thò đầu vào từ mép màn hình: 90 = đầu chĩa sang trái (núp ở mép phải), -90 = chĩa sang phải
    (mép trái), 180 = lộn ngược chúc đầu xuống (treo ở mép trên)."""
    return keyed(_base(name).rotate(angle, Image.BICUBIC))


SWING_MAX, SWING_STEP = 16, 0.5  # bị xách cổ áo: nghiêng tối đa ±16°, mỗi ảnh cách 0.5° cho mượt
SWING_PAD = 60  # khung rộng thêm mỗi bên cho chân khỏi bị cắt khi lắc (SIZE + 2*60 = bề ngang cửa sổ)
GRIP = (152, 30)  # chỗ bàn tay nắm cổ áo trên ảnh DRAG_EMOTE (ở cỡ SIZE): lắc quanh điểm này


def swing_frames(name):
    """Góc nghiêng (độ, dương = ngược chiều kim đồng hồ) -> ảnh emote name xoay quanh GRIP, rộng SIZE + 2*SWING_PAD."""
    base = Image.open(EMOTE_DIR / f"{name}.png").convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
    wide = Image.new("RGBA", (SIZE + 2 * SWING_PAD, SIZE), (0, 0, 0, 0))
    wide.paste(base, (SWING_PAD, 0))
    center = (SWING_PAD + GRIP[0], GRIP[1])
    return {a: keyed(wide.rotate(a, Image.BICUBIC, center=center))
            for a in (i * SWING_STEP for i in range(-round(SWING_MAX / SWING_STEP), round(SWING_MAX / SWING_STEP) + 1))}


def hand_images():
    """4 dáng bàn tay xoa đầu lấy từ video petpet nền xanh (ban_tay/a-d.png, cắt chung một khung nên ghép liền nhau)."""
    return {k: keyed(Image.open(ROOT / "ban_tay" / f"{k}.png").convert("RGBA")) for k in "abcd"}


def glyph(ch, fill, size):
    """Ảnh ký hiệu (Z, ♥, !) chữ đậm viền nâu, mép cứng như emote."""
    if ch == "♥":  # tim pixel do người dùng vẽ; NEAREST để ô pixel vẫn sắc khi thu nhỏ
        im = HEART_IMG.resize((round(size * 1.2), round(size * 1.2 * HEART_IMG.height / HEART_IMG.width)), Image.NEAREST)
    else:
        im = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
        if ch == "💢":  # dấu giận: emoji màu của Windows, không viền
            ImageDraw.Draw(im).text((size, size), ch, font=ImageFont.truetype("seguiemj.ttf", size), anchor="mm",
                                    embedded_color=True)
        else:
            font = ImageFont.truetype("seguisym.ttf" if ch == "✦" else "arialbd.ttf", size)  # Arial không có ✦
            ImageDraw.Draw(im).text((size, size), ch, font=font, fill=fill,
                                    anchor="mm", stroke_width=max(2, size // 9), stroke_fill="#5b3442")
        im = im.crop(im.getbbox())
    return keyed(im)


def glyph_frames():
    """Mỗi loại vài khung to -> nhỏ: bay lên thì nhỏ dần rồi biến mất (cửa sổ màu khoá không làm mờ dần được)."""
    return {kind: [glyph(ch, color, s) for s in (34, 30, 26, 22, 18, 14)]
            for kind, ch, color in (("z", "Z", "#9ec5ff"), ("heart", "♥", "#ff6b8b"), ("bang", "!", "#ffd23f"),
                                         ("note", "♪", "#f08aa0"), ("notes", "♫", "#e0607e"),
                                         ("sparkle", "✦", "#ffd84a"), ("anger", "💢", None))}


def dot_frames():
    """Ba chấm "đang nghĩ" hiện dồn: trống → 1 → 1 2 → 1 2 3 → trống... Chấm đầu luôn sát đầu: bản lật cho bên trái."""
    frames = []
    for n in range(4):
        im = Image.new("RGBA", (60, 20), (0, 0, 0, 0))
        for i in range(n):
            ImageDraw.Draw(im).ellipse((i * 20 + 2, 2, i * 20 + 17, 17), fill="#f08aa0", outline="#5b3442", width=2)
        frames.append(im)
    return [keyed(im) for im in frames], [keyed(ImageOps.mirror(im)) for im in frames]  # bên phải đầu, bên trái đầu


def food_image(ch, size=64):
    """Đồ ăn cho mini game: emoji màu của Windows (Segoe UI Emoji) vẽ thành ảnh."""
    im = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((size // 2, size // 2), ch, font=ImageFont.truetype("seguiemj.ttf", size), embedded_color=True)
    return keyed(im.crop(im.getbbox()))


def overlay(root):
    """Nhãn ảnh trong một cửa sổ trong suốt riêng đè lên nhân vật (ký hiệu bay, ba chấm đang nghĩ): đặt nhãn chung
    cửa sổ nhân vật thì chỗ màu khoá quanh ảnh "đục thủng" luôn cả nhân vật, lộ màn hình phía sau thành ô vuông."""
    win = tk.Toplevel(root)
    win.withdraw()
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.attributes("-transparentcolor", KEY)
    win.config(bg=KEY)  # nền cửa sổ cũng trong suốt: không thì lúc mới hiện lóe một ô xám
    lab = tk.Label(win, bg=KEY, bd=0)
    lab.pack()
    win.update_idletasks()
    u, h = ctypes.windll.user32, ctypes.c_void_p(int(win.wm_frame(), 16))
    u.SetWindowLongW(h, -20, u.GetWindowLongW(h, -20) | 0x08000020)  # không cướp focus, chuột bấm xuyên qua
    return lab
