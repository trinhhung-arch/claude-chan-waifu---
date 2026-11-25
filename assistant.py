"""Trợ lý màn hình: cứ INTERVAL giây chụp màn hình, gửi model vision chạy trên Mac (Ollama qua Tailscale),
rồi hiện emote + lời nói ở góc phải dưới.
Chạy:       python assistant.py
Thử giao diện không cần Mac:  python assistant.py --mock
Bấm chuột trái vào nhân vật: tạm dừng / tiếp tục nhìn màn hình.  Bấm đúp: hỏi nhân vật.
Giữ chuột trái và kéo: di chuyển.  Chuột phải: ẩn xuống khay (bấm icon ở khay để hiện lại, thoát trong menu khay).
Những điều nhân vật nhớ về bạn nằm trong ky_uc.txt (cùng thư mục), sửa hoặc xoá thoải mái.
"""
import ctypes
import io
import json
import math
import os
import queue
import random
import re
import sys
import threading
import time
import tkinter as tk
from collections import deque
from datetime import date
from pathlib import Path

import mss
import ollama
import pystray
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, ImageTk

# ===== Cấu hình =====
HOST = "http://100.105.62.59:11434"  # IP Tailscale của máy Mac (macbook-pro-ca-trnh)
MODEL = "qwen2.5vl:32b"
INTERVAL = 45  # giây giữa 2 lần nhìn màn hình
GAME_INTERVAL = 180  # khi đang chơi game / xem video toàn màn hình thì nói thưa hơn
AWAY_MINUTES = 5  # không chạm chuột/bàn phím quá chừng này phút: nhân vật ngủ gục, ngừng chụp màn hình
TIRED_HOURS = 2  # ngồi máy liên tục quá chừng này tiếng: nhân vật buồn ngủ, nhắc nghỉ (rồi mỗi tiếng nhắc lại)
NIGHT_HOURS = range(0, 5)  # từ 0h tới trước 5h sáng: nhắc đi ngủ (một lần mỗi đêm)
LOW_BATTERY = 20  # pin dưới chừng này % (mà không cắm sạc) thì nhắc
IDLE_POSES = ["mim_cuoi", "suy_tu", "le_luoi"]  # lâu không nói gì thì thỉnh thoảng tự đổi qua lại các dáng này
IDLE_POSE_SECONDS = 90  # im lặng chừng này giây thì đổi dáng một lần
WALK = True  # rảnh thì thỉnh thoảng nhảy lò cò đi dạo ngang một đoạn (bật/tắt được trong menu khay)
WALK_CHANCE = 0.3  # mỗi lần rảnh, 30% là đi dạo, còn lại là đổi dáng
FOCUS_MINUTES, BREAK_MINUTES = 25, 5  # hẹn giờ tập trung (Pomodoro) trong menu khay
FOCUS_BLOCK = ["facebook", "tiktok", "youtube", "instagram", "reddit", "twitter"]  # mở mấy trang này lúc tập trung: bị nhắc
CLIP_MAX = 2000  # "Hỏi về đoạn vừa copy" gửi tối đa chừng này ký tự
SIZE = 220  # cỡ emote (px)
BUBBLE_SECONDS = 15
PERSONA = (
    "Bạn là một cô bé tóc hồng tinh nghịch ngồi ở góc màn hình, đang xem người dùng làm việc trên máy tính. "
    "Nói tiếng Việt, xưng 'mình', gọi người dùng là 'bạn' (đừng đoán là anh hay chị), tối đa 2 câu ngắn. "
    "Bình luận cụ thể về thứ đang thấy trên màn hình: "
    "cổ vũ, trêu nhẹ, nhắc nghỉ ngơi hoặc góp ý nhỏ. Nhân vật tóc hồng ở góc phải dưới màn hình là chính bạn, bỏ qua nó."
)
# Ý nghĩa từng emote, gửi kèm cho model để nó chọn đúng (tên phải khớp file trong V3_trong_suot)
EMOTE_GUIDE = {
    "mim_cuoi": "cười hiền. Mặc định khi bình thường, cổ vũ nhẹ nhàng",
    "nhay_mat_ok": "nháy mắt làm dấu OK. Khi việc ổn rồi, làm tốt lắm, đồng ý",
    "lap_lanh": "mắt lấp lánh há miệng. Khi có tin vui, thành công, thấy thứ hay ho",
    "phan_khich": "áp sát màn hình cười toe. Khi cực kỳ hào hứng, game gay cấn, vừa thắng",
    "le_luoi": "lè lưỡi vẫy tay. Khi trêu đùa vui vẻ, chào hỏi tinh nghịch",
    "tinh_quai": "mọc sừng quỷ cười gian. Khi bày trò, trêu chọc, xúi làm chuyện nghịch",
    "de_thuong": "ôm má phụng phịu. Khi làm nũng, được khen, thấy thứ dễ thương",
    "chay_mau_mui": "mặt đơ chảy máu mũi giơ ngón cái. Khi thấy nhân vật/ảnh đẹp hoặc dễ thương quá mức",
    "mot_sach": "đeo kính răng thỏ giơ ngón cái. CHỈ khi đang giải thích một điều gì đó: chỉ ra nguyên nhân, cách làm, "
                "nghĩa của từ/đoạn code. Chỉ khen người dùng đang code/học thì dùng co_vu",
    "suy_tu": "tay chống cằm. Khi đang nghĩ, câu hỏi khó, xem người dùng đọc hay phân tích gì đó",
    "cau_nguyen": "chắp tay cầu nguyện. Khi chờ build, chạy test, tải file, nộp bài, mong kết quả tốt",
    "co_vu": "nằm trên gối vẫy hai cây lightstick. Khi cổ vũ người dùng đang chăm chỉ làm bài, học, code, viết",
    "soc": "mắt tròn há hốc. Khi thấy lỗi đỏ, chuyện bất ngờ, máu thấp, sắp thua",
    "xau_ho": "lấy tay che mặt. Khi ngại ngùng, bị khen, thấy nội dung riêng tư hoặc khó xử",
    "gian_doi": "khoanh tay phụng phịu. Khi người dùng lướt mạng xã hội thay vì làm việc, hoặc lơ mình",
    "buon": "ôm gối mắt rưng rưng. Khi làm hỏng việc, thất bại, tin buồn",
    "buon_ngu": "nằm gục lên gối. Khi đã khuya, làm việc quá lâu, nên nghỉ ngơi",
}
# Tiêu đề cửa sổ đang mở chứa một trong các từ này (không phân biệt hoa thường) thì không chụp màn hình
PRIVATE_WORDS = ["bank", "ngân hàng", "password", "mật khẩu", "inprivate", "incognito", "ẩn danh",
                 "đăng nhập", "sign in", "login", "log in", "1password", "bitwarden", "keepass",
                 "momo", "zalopay", "vnpay", "paypal"]
MAX_MEMORY = 30  # nhớ tối đa chừng này điều về bạn, quá thì quên điều cũ nhất
HISTORY_TURNS = 3  # gửi kèm chừng này cặp hỏi-đáp gần nhất để hỏi tiếp được ("còn cái kia thì sao?")
# Câu nhân vật tự nói (không qua model). Mỗi lần chọn ngẫu nhiên một câu cho đỡ nhàm; thêm bớt thoải mái.
# {n} = " Tên" (hoặc trống), {h} = số tiếng, {p} = % pin, {m}/{b} = phút tập trung/nghỉ, {what} = việc cần nhắc
LINES = {
    "morning": ["Chào buổi sáng{n}! Hôm nay mình làm gì nè?", "Sáng rồi{n}! Uống nước chưa đó?",
                "Chào buổi sáng{n}~ Hôm nay cố lên nha!"],
    "noon": ["Trưa rồi{n}, ăn cơm chưa đó?", "Giữa trưa rồi{n}, nghỉ ăn chút đi nha~", "Trưa rồi nè{n}, đói chưa?"],
    "afternoon": ["Chào buổi chiều{n}! Cố lên nha.", "Chiều rồi{n}~ Uống miếng nước đi.", "Buổi chiều vui vẻ nha{n}!"],
    "evening": ["Tối rồi{n}, vẫn còn làm à?", "Chào buổi tối{n}~ Ăn tối chưa?", "Tối rồi nè{n}, làm xong sớm rồi nghỉ nha."],
    "late": ["Khuya rồi đó{n}... đừng thức muộn quá nha.", "Giờ này còn thức hả{n}? Ngủ sớm đi mà~",
             "Khuya lắm rồi{n}... mình buồn ngủ ghê."],
    "monday": ["Thứ Hai rồi{n}! Đầu tuần cố lên nha!", "Đầu tuần rồi{n}~ Tuần này mình làm gì nè?"],
    "friday": ["Thứ Sáu rồi{n}! Sắp cuối tuần rồi~", "Thứ Sáu nè{n}! Ráng nốt hôm nay thôi!"],
    "birthday": ["Chúc mừng sinh nhật{n}!!! Hôm nay phải vui thật nhiều nha!", "Sinh nhật vui vẻ{n}! Mình chúc bạn mọi điều tốt nhất~"],
    "tet": ["Chúc mừng năm mới{n}! An khang thịnh vượng nha~", "Tết vui vẻ{n}! Năm mới nhiều may mắn nè!"],
    "trung_thu": ["Trung thu vui vẻ{n}! Ăn bánh trung thu chưa?", "Rằm tháng Tám rồi{n}~ Trăng hôm nay chắc đẹp lắm!"],
    "pause": ["Mình che mắt rồi nha, bấm lại để mình xem tiếp.", "Không nhìn, không nhìn! Bấm lại khi nào cần mình nha.",
              "Ok, mình nhắm mắt đây~"],
    "resume": ["Mình xem tiếp đây!", "Mở mắt rồi nè!", "Cho mình xem tiếp với~"],
    "private": ["Chỗ này riêng tư, mình không nhìn đâu nha.", "Ơ, chỗ này riêng tư, mình quay đi đây~",
                "Mình che mắt chỗ này nha, yên tâm!"],
    "offline": ["Mình mất kết nối với máy Mac rồi... thử lại sau nha.", "Ơ, máy Mac không trả lời mình... lát thử lại nha."],
    "ask_fail": ["Mình không hỏi được máy Mac... thử lại sau nha.", "Máy Mac không trả lời rồi, hỏi lại sau nha..."],
    "ask_hint": ["Bạn muốn hỏi gì nè? Enter để gửi, Esc để thôi.", "Hỏi mình đi~ Enter để gửi, Esc để thôi."],
    "thinking": ["Để mình xem nào...", "Hmm, đợi mình chút...", "Để mình nghĩ đã~"],
    "away": ["Zzz... bạn đi đâu rồi, mình ngủ chút nha.", "Bạn đi đâu rồi... mình chợp mắt tí~", "Zzz..."],
    "back": ["A, bạn về rồi!", "Bạn về rồi nè! Mình đợi mãi~", "Ủa, về rồi hả? Làm tiếp thôi!"],
    "tired": ["Bạn ngồi {h} tiếng rồi đó... mình buồn ngủ quá, nghỉ chút đi.",
              "{h} tiếng rồi đó! Đứng dậy vươn vai chút đi mà~", "Ngồi {h} tiếng liền rồi... mắt mỏi chưa? Nghỉ tí nha."],
    "night": ["Quá 12 giờ đêm rồi... mình buồn ngủ quá, đi ngủ thôi.", "Nửa đêm rồi đó... mai làm tiếp nha, đi ngủ đi~"],
    "pat": ["Hehe, nhột quá~", "Xoa nữa đi~", "Ư ư... nhột mà!", "Hihi, thích ghê~"],
    "dragged": ["Ơ ơ, đi đâu vậy!", "Á á, thả mình xuống~", "Đừng xách cổ áo mình mà!", "Huhu, chóng mặt quá~"],
    "dropped": ["Hạ cánh an toàn~", "Phù, chỗ mới cũng được nè.", "Lần sau báo trước nha!", "Ui, tới nơi rồi hả?"],
    "battery": ["Pin còn {p}% thôi, cắm sạc đi kẻo sập máy!", "Ơ, pin còn có {p}%! Sạc đi sạc đi!"],
    "net_lost": ["Ơ... mất mạng rồi.", "Mạng đi đâu mất rồi..."],
    "net_back": ["Có mạng lại rồi!", "Mạng về rồi nè!"],
    "focus_start": ["Bắt đầu {m} phút tập trung! Cố lên nha!", "{m} phút tập trung nè, mình canh cho!"],
    "focus_stop": ["Dừng tập trung rồi nha.", "Ok, nghỉ tập trung nha~"],
    "focus_nag": ["Đang giờ tập trung mà! Tắt đi rồi làm tiếp nào.", "Ê ê, đang tập trung mà lướt gì đó?", "Hứ, hết giờ rồi hẵng xem!"],
    "focus_done": ["Xong {m} phút rồi, giỏi ghê! Nghỉ {b} phút đi, đứng dậy vươn vai nè.",
                   "Hết giờ tập trung! Nghỉ {b} phút cho mắt đỡ mỏi nha~"],
    "break_done": ["Hết giờ nghỉ rồi, quay lại làm tiếp nha!", "Nghỉ đủ rồi đó~ Làm tiếp thôi!"],
    "reminder": ["Đến giờ rồi nè: {what}!", "Ê, nhớ {what} nha!", "Tới giờ {what} rồi đó!"],
    "clip_empty": ["Bạn chưa copy chữ nào hết á. Bôi đen rồi Ctrl+C trước nha.", "Clipboard trống trơn à~ Copy chữ trước đã nha."],
    "clip_read": ["Để mình đọc đoạn bạn copy nào...", "Để mình xem đoạn này..."],
    "code": ["Code thôi nào!", "Mở code rồi kìa, cố lên!", "Lại code hả? Mình ngồi xem nha~"],
    "game": ["Chơi game hả? Cho mình xem với!", "Game gì đó? Thắng nha!", "Yay, giờ chơi game~"],
    "chat": ["Nhắn tin với ai đó~", "Ai nhắn đó? Hihi~", "Tám chuyện hả?"],
}
# Emote có con ngươi liếc hẳn sang một bên (ảnh gốc chưa lật): lật ảnh cho mắt nhìn về phía con trỏ chuột.
# Chỉ tính theo con ngươi, không theo độ nghiêng đầu: emote mắt nhìn thẳng mà lật theo nghiêng đầu thì trông như nhìn ngược.
FACING = {"soc": "right", "suy_tu": "right"}
# Âm lịch tra bảng (Tết = mùng 1 tháng Giêng, Trung thu = rằm tháng Tám), tới 2030
LUNAR = {"tet": ["2026-02-17", "2027-02-06", "2028-01-26", "2029-02-13", "2030-02-03"],
         "trung_thu": ["2026-09-25", "2027-09-15", "2028-10-03", "2029-09-22", "2030-09-12"]}
# Tiêu đề cửa sổ chứa từ này -> phản ứng ngay (không cần model). Game toàn màn hình nhận ra riêng.
APPS = {"code": ["visual studio code", "pycharm", "sublime text", "notepad++", "cursor"],
        "game": ["steam", "epic games", "riot client", "battle.net"],
        "chat": ["zalo", "messenger", "discord", "telegram"]}
APP_EMOTES = {"code": "co_vu", "game": "phan_khich", "chat": "tinh_quai"}  # mở code = bắt đầu làm bài: cổ vũ
APP_COOLDOWN_MINUTES = 10  # cùng một loại app thì 10 phút mới phản ứng lại một lần
APP_QUIET_SECONDS = 20  # vừa nói câu khác chưa tới chừng này giây thì không phản ứng app, khỏi chen ngang
# =====================

EMOTE_DIR = Path(__file__).parent / "V3_trong_suot"
EMOTES = sorted(p.stem for p in EMOTE_DIR.glob("*.png"))
DRAG_EMOTE = "bi_keo"  # ảnh lúc bị nhấc lên kéo đi: chỉ dùng khi kéo, model không được chọn
CHAT_EMOTES = [e for e in EMOTES if e != DRAG_EMOTE]  # emote model được chọn khi nói
POS_FILE = Path(__file__).parent / "vi_tri.txt"  # vị trí nhân vật sau lần kéo gần nhất
LOG_FILE = Path(__file__).parent / "nhat_ky.txt"  # giờ, loại, emote, câu nói (chỉ chữ, không lưu ảnh)
MEMORY_FILE = Path(__file__).parent / "ky_uc.txt"  # điều nhân vật nhớ về bạn, mỗi dòng một điều, sửa/xoá thoải mái
HEART_IMG = Image.open(Path(__file__).parent / "tim_pixel.png").convert("RGBA")  # tim pixel bay ra khi được xoa đầu
MEMORY_HEADER = "# Những điều nhân vật nhớ về bạn. Sửa hoặc xoá thoải mái, mỗi dòng một điều.\n"
SECRET_WORDS = ["mật khẩu", "password", "otp", "số tài khoản", "số thẻ", "cvv"]  # không bao giờ ghi nhớ
KEY = "#ff00fe"  # màu được Windows coi là trong suốt
TITLE = "Trợ lý màn hình"  # tiêu đề cửa sổ nhân vật, để nhận ra khi người dùng đang bấm vào nó
MOCK = "--mock" in sys.argv
# Emote mới thêm mà chưa có mô tả thì model chỉ thấy tên
SYSTEM = PERSONA + "\n\nChọn emote khớp với cảm xúc của câu bạn nói:\n" + "\n".join(
    f"- {e}: {EMOTE_GUIDE.get(e, e.replace('_', ' '))}" for e in CHAT_EMOTES)


def parse(content):
    """Câu trả lời của model -> (lời nói, emote); emote lạ thì về mim_cuoi."""
    try:
        data = json.loads(content)
        line, emote = str(data.get("loi_noi", "")).strip(), data.get("emote")
    except (json.JSONDecodeError, AttributeError):
        line, emote = str(content).strip(), None
    return line or "...", emote if emote in CHAT_EMOTES else "mim_cuoi"


def parse_facts(content):
    """Lấy danh sách "ghi_nho" trong câu trả lời của model; hỏng thì coi như không có gì mới."""
    try:
        facts = json.loads(content).get("ghi_nho", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    if not isinstance(facts, list):
        return []
    return [" ".join(str(f).split())[:200] for f in facts if str(f).strip()][:5]


def parse_reminder(content):
    """"nhac_phut"/"nhac_viec" trong câu trả lời -> (phút, việc), hoặc None nếu không nhờ nhắc / số phút vô lý."""
    try:
        data = json.loads(content)
        minutes, what = int(data.get("nhac_phut") or 0), " ".join(str(data.get("nhac_viec") or "").split())
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return None
    return (minutes, what[:100] or "việc bạn nhờ") if 1 <= minutes <= 24 * 60 else None


def parse_focus(content):
    """"tap_trung_phut" -> số phút người dùng nói sẽ làm việc/học tập trung (1-240), không có thì None."""
    try:
        minutes = int(json.loads(content).get("tap_trung_phut") or 0)
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return None
    return minutes if 1 <= minutes <= 240 else None


def load_memory(path=None):
    """Đọc lại file mỗi lần dùng, để chỗ người dùng tự sửa/xoá trong file có tác dụng ngay."""
    try:
        lines = (path or MEMORY_FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [s.strip() for s in lines if s.strip() and not s.startswith("#")][-MAX_MEMORY:]


def remember(facts, path=None):
    """Thêm điều mới vào file: bỏ trùng, bỏ thứ bí mật (mật khẩu, dãy số dài như số tài khoản/số thẻ),
    giữ MAX_MEMORY điều mới nhất. Trả về danh sách điều thật sự được thêm."""
    path = path or MEMORY_FILE
    memory = load_memory(path)
    new = [f for f in dict.fromkeys(facts) if f not in memory and not any(w in f.lower() for w in SECRET_WORDS)
           and not re.search(r"\d{8,}", f.replace(" ", "").replace(".", "").replace("-", ""))]
    if new:
        try:
            path.write_text(MEMORY_HEADER + "\n".join((memory + new)[-MAX_MEMORY:]) + "\n", encoding="utf-8")
        except OSError as e:  # file đang bị khoá: lần sau nhớ lại
            print("Không ghi được ký ức:", repr(e), file=sys.stderr)
            return []
    return new


def screenshot():
    with mss.MSS() as s:
        shot = s.grab(s.monitors[1])  # màn hình chính
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    img.thumbnail((1024, 1024))  # đủ để model đọc chữ mà ảnh vẫn nhẹ (~150KB)
    return img  # chỉ nằm trong RAM, không ghi ra đĩa


def log_line(kind, emote, line, path=LOG_FILE):
    """Ghi một dòng, các cột cách nhau bằng tab, để sau đọc lại xem model chọn emote có hợp không."""
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{kind}\t{emote}\t{' '.join(line.split())}\n")
    except OSError as e:  # file đang bị khoá (OneDrive đồng bộ...): bỏ dòng này, đừng làm treo nhân vật
        print("Không ghi được nhật ký:", repr(e), file=sys.stderr)


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


def name_from(memory):
    """Tên người dùng trong ký ức, vd "Người dùng tên Hùng" / "Mình tên là Hùng" -> "Hùng"; không có thì ""."""
    for fact in memory:
        m = re.search(r"\btên\s+(?:là\s+)?(\w+)", fact, re.IGNORECASE)  # model hay ghi "Tên là Hùng"
        if m and m.group(1)[0].isupper():
            return m.group(1)
    return ""


def pick(key, **kw):
    """Một câu ngẫu nhiên trong LINES[key], điền {n}, {h}, {p}... (thừa tham số thì bỏ qua)."""
    return random.choice(LINES[key]).format(**kw)


def greeting(hour, name=""):
    """Câu chào theo giờ -> (lời, emote)."""
    n = f" {name}" if name else ""
    for start, end, key, emote in ((5, 11, "morning", "nhay_mat_ok"), (11, 14, "noon", "mim_cuoi"),
                                   (14, 18, "afternoon", "le_luoi"), (18, 22, "evening", "suy_tu")):
        if start <= hour < end:
            return pick(key, n=n), emote
    return pick("late", n=n), "buon_ngu"


def birthday_from(memory):
    """(ngày, tháng) sinh nhật trong ký ức, vd "Sinh nhật ngày 12/5", "sinh nhật 12 tháng 5"; không có thì None."""
    for fact in memory:
        if "sinh nhật" in fact.lower():
            m = re.search(r"(\d{1,2})\s*(?:/|-|\.|\s+tháng\s+)\s*(\d{1,2})", fact)
            if m and 1 <= int(m.group(1)) <= 31 and 1 <= int(m.group(2)) <= 12:
                return int(m.group(1)), int(m.group(2))
    return None


def special_day(today, hour, memory, name=""):
    """Câu chào dịp đặc biệt -> (lời, emote), không có thì None. Sinh nhật > Tết (mùng 1-3) > Trung thu: chào cả ngày;
    thứ Hai / thứ Sáu: chỉ chào ban ngày (5h-18h), tối khuya thì để câu chào theo giờ nhắc đi ngủ."""
    n = f" {name}" if name else ""
    if birthday_from(memory) == (today.day, today.month):
        return pick("birthday", n=n), "phan_khich"
    iso = [date.fromisoformat(d) for d in LUNAR["tet"]]
    if any(0 <= (today - d).days <= 2 for d in iso):
        return pick("tet", n=n), "lap_lanh"
    if today.isoformat() in LUNAR["trung_thu"]:
        return pick("trung_thu", n=n), "lap_lanh"
    if 5 <= hour < 18 and today.weekday() in (0, 4):
        return pick("monday" if today.weekday() == 0 else "friday", n=n), "co_vu" if today.weekday() == 0 else "phan_khich"
    return None


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


def chat(client, prompt, jpeg=None, history=(), learn=False):
    """Gọi model -> (lời nói, emote, điều mới cần nhớ, lời nhờ nhắc (phút, việc) hoặc None, số phút tập trung hoặc None).
    history: các lượt hỏi-đáp trước (chỉ chữ).  learn=True (chỉ khi trả lời câu người dùng tự gõ, không học từ ảnh
    màn hình): model liệt kê điều mới đáng nhớ, lời nhờ nhắc việc, và phiên làm việc N phút nếu người dùng nói tới."""
    memory = load_memory()
    system = SYSTEM + ("\n\nNhững điều bạn nhớ về người dùng (dùng khi hợp lúc, đừng lần nào cũng nhắc):\n"
                       + "\n".join(f"- {m}" for m in memory) if memory else "")
    props = {"loi_noi": {"type": "string"}, "emote": {"type": "string", "enum": CHAT_EMOTES}}
    if learn:
        props["ghi_nho"] = {"type": "array", "items": {"type": "string"}}
        prompt += (' Trong "ghi_nho", liệt kê điều MỚI đáng nhớ lâu dài mà người dùng vừa tự nói về bản thân'
                   " (tên, sở thích, dự án lâu dài, ngày quan trọng như sinh nhật...), mỗi điều một câu ngắn;"
                   " không có gì mới thì để []. Không ghi việc tạm thời trong hôm nay (đang làm gì trong bao lâu,"
                   " hẹn giờ, lời nhắc), không ghi mật khẩu, số tài khoản, mã OTP.")
        props["nhac_phut"], props["nhac_viec"] = {"type": "integer"}, {"type": "string"}
        props["tap_trung_phut"] = {"type": "integer"}
        prompt += (f" Bây giờ là {time.strftime('%H:%M')}. Nếu người dùng nói sắp làm việc / học / code / tập trung"
                   ' trong một khoảng thời gian (vd "mình code 40 phút", "làm bài nửa tiếng", "học 1 tiếng"), điền'
                   ' "tap_trung_phut" = số phút đó và để "nhac_phut" = 0 (app tự canh giờ, hết giờ sẽ nhắc nghỉ).'
                   ' Còn nếu người dùng nhờ nhắc một việc khác sau một lúc hay vào một giờ trong 24 giờ tới, điền'
                   ' "nhac_phut" = số phút tính từ bây giờ và "nhac_viec" = việc cần nhắc. Không có thì để 0 và "".')
    msg = {"role": "user", "content": prompt}
    if jpeg:
        msg["images"] = [jpeg]
    r = client.chat(
        model=MODEL,
        messages=[{"role": "system", "content": system}, *history, msg],
        format={  # Ollama ép model trả đúng JSON này, emote chỉ được nằm trong danh sách
            "type": "object",
            "properties": props,
            "required": list(props),
        },
        # num_ctx: mặc định Ollama chỉ đọc 2-4 nghìn token, ký ức + lịch sử + ảnh sẽ bị cắt mất phần đầu mà không báo
        options={"temperature": 0.8, "num_ctx": 8192},
        keep_alive="30m",
    )
    content = r.message.content
    if not learn:
        return (*parse(content), [], None, None)
    return (*parse(content), parse_facts(content), parse_reminder(content), parse_focus(content))


def worker(out, paused, asks, seen, sleeping, hidden):
    """out nhận (lời, emote) = bình luận, hoặc (lời, emote, True, nhắc, tập trung) = trả lời câu hỏi (hiện cả khi đang
    tạm dừng), nhắc = (phút, việc) nếu nhờ nhắc việc, tập trung = số phút nếu người dùng nói sắp làm việc bao lâu.
    asks: câu người dùng hỏi.  seen["title"]: tiêu đề cửa sổ khác gần nhất (khi người dùng đang bấm vào nhân vật)."""
    client = ollama.Client(host=HOST, timeout=180)
    recent = deque(maxlen=3)  # câu bình luận gần nhất
    history = deque(maxlen=HISTORY_TURNS * 2)  # các lượt hỏi-đáp gần nhất, chỉ trong RAM
    last = None  # ảnh đã gửi model lần gần nhất
    hiding = False  # đang ở cửa sổ riêng tư
    offline = False  # đã báo mất kết nối chưa
    wait = 3
    while True:
        try:  # chờ tới lượt nhìn màn hình, nhưng có câu hỏi thì trả lời ngay
            question = asks.get(timeout=wait)
        except queue.Empty:
            question = None
        # chơi game / xem video toàn màn hình: nói thưa hơn cho đỡ phiền
        wait = (15 if MOCK else GAME_INTERVAL) if fullscreen() else (5 if MOCK else INTERVAL)
        title = active_title()
        title = seen["title"] if title == TITLE else title  # đang bấm vào nhân vật thì xét cửa sổ trước đó
        if question is not None:
            # ("clip", chữ): hỏi về đoạn vừa copy -> chỉ gửi chữ đó, không chụp màn hình, không học, không nhắc việc
            clip = isinstance(question, tuple)
            text, remind, focus = (question[1] if clip else question), None, None
            try:
                blind = clip or paused.is_set() or is_private(title)  # tạm dừng / riêng tư: trả lời mà không nhìn màn hình
                if clip:
                    prompt = ("Người dùng vừa copy đoạn dưới đây và nhờ bạn: nếu là code thì giải thích nó làm gì (và chỉ ra"
                              " lỗi nếu thấy), nếu là tiếng nước ngoài thì dịch sang tiếng Việt, còn lại thì tóm tắt ý chính."
                              f" Tối đa 3 câu ngắn, rồi chọn emote hợp cảm xúc.\n---\n{text}\n---")
                else:
                    prompt = (f'Người dùng hỏi bạn: "{text}". Trả lời đúng câu hỏi, tối đa 3 câu ngắn, rồi chọn emote hợp cảm xúc.'
                              + (" Lúc này bạn KHÔNG được xem màn hình, chỉ trả lời bằng hiểu biết của mình." if blind
                                 else " Dựa vào ảnh màn hình nếu câu hỏi liên quan."))
                    if recent:
                        prompt += " Những câu bạn vừa tự bình luận: " + " | ".join(recent)
                if MOCK:  # giả lập: "nhớ" -> ghi nhớ nguyên câu; "nhắc ... N phút" -> hẹn; "làm/học/code ... N phút" -> tập trung
                    line = (f"(thử) Đoạn bạn copy: {text[:40]}..." if clip
                            else f"(thử) Bạn hỏi: {text}" + (" (mình không nhìn màn hình)" if blind else ""))
                    emote, facts = random.choice(CHAT_EMOTES), ([text] if not clip and "nhớ" in text.lower() else [])
                    m, low = re.search(r"(\d+)\s*phút", text), text.lower()
                    if m and not clip and "nhắc" in low:
                        remind = (int(m.group(1)), text)
                    elif m and not clip and any(w in low for w in ("tập trung", "làm", "học", "code")):
                        focus = int(m.group(1))
                else:
                    line, emote, facts, remind, focus = chat(client, prompt, None if blind else to_jpeg(screenshot()),
                                                             list(history), learn=not clip)
                if clip:  # giải thích / dịch đoạn vừa copy luôn là lúc giải thích: đeo kính mọt sách
                    emote = "mot_sach"
                history.extend([{"role": "user", "content": f"[đoạn vừa copy] {text[:300]}" if clip else text},
                                {"role": "assistant", "content": line}])
                if remember(facts):
                    line += " (Mình nhớ rồi nha!)"
                at = lambda minutes: time.strftime('%H:%M', time.localtime(time.time() + minutes * 60))
                if focus:  # phiên làm việc: app canh giờ + nhắc nghỉ, không cần thêm lời nhắc trùng
                    remind = None
                    line += f" (Bắt đầu tập trung {focus} phút, xong lúc {at(focus)})"
                if remind:
                    line += f" (Mình sẽ nhắc lúc {at(remind[0])})"
            except Exception as e:
                print("Lỗi:", repr(e), file=sys.stderr)
                line, emote, remind, focus = pick("ask_fail"), "buon", None, None
            out.put((line, emote, True, remind, focus))
            continue
        # đang ngủ (người dùng rời máy) hoặc bị ẩn xuống khay thì không chụp, Mac đỡ tốn GPU
        if not (paused.is_set() or sleeping.is_set() or hidden.is_set()):
            try:
                if is_private(title):  # kiểm tra ngay trước lúc chụp; riêng tư thì không chụp gì cả
                    if not hiding:
                        out.put((pick("private"), "xau_ho"))
                    hiding = True
                else:
                    hiding = False
                    img = screenshot()
                    if not changed(img, last):
                        print("Bỏ qua: màn hình gần như không đổi", file=sys.stderr)
                    else:
                        jpeg = to_jpeg(img)
                        if MOCK:
                            line, emote = f"(thử) Ảnh màn hình {len(jpeg) // 1024}KB, mình thấy rồi nha!", random.choice(CHAT_EMOTES)
                        else:
                            prompt = "Người dùng đang làm gì trên màn hình? Nói một câu với họ và chọn emote hợp cảm xúc."
                            if recent:
                                prompt += " Những câu bạn vừa nói (đừng lặp lại): " + " | ".join(recent)
                            line, emote, *_ = chat(client, prompt, jpeg)  # bình luận màn hình: không học, không nhắc
                        last = img  # chỉ nhớ khi gửi thành công, lỗi thì lượt sau gửi lại
                        recent.append(line)
                        out.put((line, emote))
                        offline = False
            except Exception as e:  # Mac tắt, mất mạng, model chưa tải...
                print("Lỗi:", repr(e), file=sys.stderr)
                if not offline:  # báo một lần mỗi đợt mất kết nối, không nhắc lại mỗi lượt
                    out.put((pick("offline"), "buon"))
                offline = True


def main():
    # Màn hình scale 125%: không bật cái này thì Tk báo sai kích thước màn hình, nhân vật lệch khỏi góc
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    if sys.stderr is None:  # chạy bằng pythonw (tự khởi động) không có console: ghi lỗi ra file, mỗi lần chạy ghi đè
        sys.stderr = open(Path(__file__).parent / "assistant.log", "w", encoding="utf-8")
    root = tk.Tk()
    root.title(TITLE)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", KEY)
    root.config(bg=KEY)
    W, H = 340, SIZE + 170  # 170px phía trên đủ cho bong bóng 4 dòng
    ABOVE_ENTRY = H - SIZE - 34  # đáy bong bóng khi ô hỏi đang mở: nằm trên ô hỏi
    work = (ctypes.c_long * 4)()  # vùng làm việc = màn hình trừ taskbar (trái, trên, phải, dưới)
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, work, 0)  # SPI_GETWORKAREA
    x, y = work[2] - W, work[3] - H  # mặc định: góc phải, đáy sát mép trên taskbar
    try:  # vị trí đã kéo lần trước, nếu vẫn nằm trong màn hình
        sx, sy = map(int, POS_FILE.read_text().split())
        # shortcut: chỉ nhận màn hình chính, màn phụ toạ độ âm sẽ về góc mặc định; cần thì dùng monitor của mss
        if 0 <= sx <= root.winfo_screenwidth() - 50 and 0 <= sy <= root.winfo_screenheight() - 50:
            x, y = sx, sy
    except (OSError, ValueError):
        pass
    root.geometry(f"{W}x{H}+{x}+{y}")

    BREATH = 5  # thở: thân cao thêm tối đa 5px (~2%), đáy giữ nguyên
    pics = {}  # (tên emote, lật?) -> [khung cao SIZE, SIZE+1, ..., SIZE+BREATH]
    for name in EMOTES:
        base = Image.open(EMOTE_DIR / f"{name}.png").convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
        for flip in (False, True):
            src, pics[name, flip] = ImageOps.mirror(base) if flip else base, []
            for k in range(BREATH + 1):
                im = src.resize((SIZE, SIZE + k), Image.BICUBIC)
                # Màu khoá chỉ trong suốt 0/1: cắt alpha ở 50% để mép không bị viền hồng của KEY
                bg = Image.new("RGBA", im.size, KEY)
                bg.paste(im, mask=im.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
                pics[name, flip].append(ImageTk.PhotoImage(bg.convert("RGB")))
    # emote đang hiện, khung thở, lật theo chuột, quay ngoắt (dỗi)
    cur = {"emote": "mim_cuoi", "k": 0, "mouse_flip": False, "turn": False, "mouse_side": None}
    walk = {"on": WALK, "dir": None, "job": None, "x0": 0}  # đi dạo: bật/tắt, hướng đang đi, vòng hẹn giờ, x lúc xuất phát

    def render():
        """Vẽ lại nhân vật theo cur; ảnh không đổi thì thôi (gọi 60 lần/giây lúc chuyển động vẫn nhẹ)."""
        img = pics[cur["emote"], cur["mouse_flip"] != cur["turn"]][cur["k"]]
        if face.cget("image") != str(img):
            face.config(image=img)

    def look():
        """Quay mặt theo chuột: emote đang nghiêng một phía (FACING) thì lật cho mặt hướng về con trỏ.
        Chuột ngay giữa nhân vật (±15px) thì giữ phía cũ, khỏi lật qua lật lại khi chuột đứng yên đúng chính giữa."""
        dx = root.winfo_pointerx() - (root.winfo_rootx() + W // 2)
        if abs(dx) > 15:
            cur["mouse_side"] = "left" if dx < 0 else "right"
        # Tính lại từ phía chuột đã nhớ cho MỖI emote: emote mới có thể vốn nghiêng phía khác emote cũ, nên không được
        # giữ nguyên trạng thái lật cũ (chuột đang ở gần giữa lúc vừa xoa đầu / bấm / thả ra thì sẽ quay ngược).
        side, want = FACING.get(cur["emote"]), walk["dir"] or cur["mouse_side"]  # đang đi dạo: nhìn hướng đi
        cur["mouse_flip"] = bool(side and want and side != want)

    def follow_mouse():
        look()
        render()
        root.after(40, follow_mouse)  # 25 lần/giây: rê chuột nhanh vẫn theo kịp; chỉ đổi ảnh khi hướng thật sự đổi nên nhẹ

    def breathe():
        """Hít vào thở ra một nhịp mỗi 3.5 giây."""
        cur["k"] = round(BREATH * (1 - math.cos(2 * math.pi * time.perf_counter() / 3.5)) / 2)
        render()
        root.after(50, breathe)

    face = tk.Label(root, image=pics["mim_cuoi", False][0], bg=KEY, bd=0, cursor="hand2")
    face.place(relx=0.5, rely=1, anchor="s")  # cùng trục giữa với bong bóng
    bubble = tk.Canvas(root, bg=KEY, highlightthickness=0)
    hide_job, typing = [None], [None]

    def type_out(item, line, n=1):
        """Chữ hiện dần từng ký tự như đang gõ, ~35 ký tự/giây."""
        bubble.itemconfig(item, text=line[:n])
        typing[0] = root.after(28, type_out, item, line, n + 1) if n < len(line) else None

    def draw_bubble(line):
        """Bong bóng bo góc, viền hồng theo màu tóc, bóng đổ nhạt, đuôi nhọn chỉ xuống nhân vật."""
        c, pad, r, tail = bubble, 14, 16, 12
        if typing[0]:
            root.after_cancel(typing[0])
        c.delete("all")
        text = c.create_text(pad + 2, pad, text=line, anchor="nw", width=W - 2 * pad - 10,
                             font=("Segoe UI", 11), fill="#5b3442")
        x1, y1 = c.bbox(text)[2] + pad, c.bbox(text)[3] + pad - 2
        for d, fill, edge in ((4, "#e8c3cf", ""), (0, "#fff8fb", "#f08aa0")):  # bóng đổ trước, thân sau
            x0, y0, X, Y, cx = 2 + d, 2 + d, x1 + d, y1 + d, (x1 + 2) / 2 + d
            # điểm lặp đôi = đoạn thẳng / góc nhọn khi smooth=True; chỉ 4 góc khung được bo
            pts = [x0 + r, y0, x0 + r, y0, X - r, y0, X - r, y0, X, y0, X, y0 + r, X, y0 + r, X, Y - r, X, Y - r, X, Y,
                   X - r, Y, X - r, Y, cx + 10, Y, cx + 10, Y, cx, Y + tail, cx, Y + tail, cx - 10, Y, cx - 10, Y,
                   x0 + r, Y, x0 + r, Y, x0, Y, x0, Y - r, x0, Y - r, x0, y0 + r, x0, y0 + r, x0, y0]
            c.create_polygon(pts, smooth=True, fill=fill, outline=edge, width=2)
        c.tag_raise(text)
        c.config(width=x1 + 8, height=y1 + tail + 8)  # cỡ bong bóng tính theo cả câu, rồi mới gõ dần
        type_out(text, line)

    def show_bubble(line, y=None):
        draw_bubble(line)
        if y is None:  # ô hỏi đang mở thì mọi câu (tạm dừng, nhột, nhắc việc...) nổi lên trên ô, không che chỗ gõ
            y = ABOVE_ENTRY if entry.winfo_ismapped() else H - SIZE + 14
        bubble.place(relx=0.5, y=y, anchor="s")
        if hide_job[0]:
            root.after_cancel(hide_job[0])
        hide_job[0] = root.after(BUBBLE_SECONDS * 1000 + len(line) * 28, done_talking)  # cộng thời gian gõ

    def done_talking():
        """Nói xong (bong bóng ẩn): về dáng bình thường mim_cuoi. Trạng thái kéo dài thì giữ nguyên:
        đang ngủ (buon_ngu), đang tạm dừng (xau_ho che mắt), đang bị kéo (bi_keo)."""
        bubble.place_forget()
        if not (sleeping.is_set() or paused.is_set() or "prev" in drag) and cur["emote"] != "mim_cuoi":
            cur["emote"] = "mim_cuoi"
            look()
            render()

    hop = [None]

    def motion(emote):
        """Đường đi từng khung (~60 khung/giây): (dx, dy lên trên, quay_ngoắt). Mỗi cảm xúc một kiểu:
        vui nhảy 2 nhịp cao, sốc giật nảy rồi rung lắc, buồn chùng xuống rồi từ từ lên, buồn ngủ gật gù 2 cái,
        dỗi quay ngoắt đi rồi quay lại, cổ vũ lật qua lật lại như vẫy lightstick; còn lại nhún 1 nhịp + nảy nhẹ."""
        hop1 = lambda h, n: [(0, h * math.sin(math.pi * i / n), 0) for i in range(n + 1)]
        if emote in ("lap_lanh", "phan_khich"):
            path = hop1(24, 14) + hop1(16, 12)
        elif emote == "co_vu":  # cổ vũ: lật ảnh qua lại 8 lần như đang vẫy lightstick, mỗi lần nảy nhẹ (~1.3s)
            path = [(0, 6 * math.sin(math.pi * (i % 10) / 10), (i // 10) % 2) for i in range(80)]
        elif emote == "soc":
            path = hop1(14, 8) + [(round(7 * math.sin(i * 1.7) * (1 - i / 24)), 0, 0) for i in range(24)]
        elif emote == "buon":
            path = [(0, -10 * i / 30, 0) for i in range(30)] + [(0, -10, 0)] * 40 + [(0, -10 * (1 - i / 50), 0) for i in range(51)]
        elif emote == "buon_ngu":
            path = [(0, -7 * math.sin(math.pi * i / 45) ** 2, 0) for i in range(91)]
        elif emote == "gian_doi":
            path = [(0, 8 * math.sin(math.pi * i / 8), 1) for i in range(9)] + [(0, 0, 1)] * 50 + [(0, 0, 0)]
        else:
            path = hop1(18, 14) + hop1(5, 7)
        return path + [(0, 0, 0)]

    def animate(path, i=0):
        dx, dy, turn = path[i]
        cur["turn"] = bool(turn)
        face.place_configure(x=dx, y=-round(dy))
        render()
        hop[0] = root.after(16, animate, path, i + 1) if i + 1 < len(path) else None

    def glyph(ch, fill, size):
        """Ảnh ký hiệu (Z, ♥, !) chữ đậm viền nâu, mép cứng như emote (màu khoá chỉ trong suốt 0/1)."""
        if ch == "♥":  # tim pixel do người dùng vẽ; NEAREST để ô pixel vẫn sắc khi thu nhỏ
            im = HEART_IMG.resize((round(size * 1.2), round(size * 1.2 * HEART_IMG.height / HEART_IMG.width)), Image.NEAREST)
        else:
            im = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((size, size), ch, font=ImageFont.truetype("arialbd.ttf", size), fill=fill,
                                    anchor="mm", stroke_width=max(2, size // 9), stroke_fill="#5b3442")
            im = im.crop(im.getbbox())
        bg = Image.new("RGBA", im.size, KEY)
        bg.paste(im, mask=im.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
        return ImageTk.PhotoImage(bg.convert("RGB"))

    # mỗi loại vài khung to -> nhỏ: bay lên thì nhỏ dần rồi biến mất (cửa sổ màu khoá không làm mờ dần được)
    glyphs = {kind: [glyph(ch, color, s) for s in (34, 30, 26, 22, 18, 14)]
              for kind, ch, color in (("z", "Z", "#9ec5ff"), ("heart", "♥", "#ff6b8b"), ("bang", "!", "#ffd23f"))}

    def puff(kind, x, y, step=0, lab=None):
        """Một ký hiệu bay lên ~50px, lắc lư nhẹ, nhỏ dần rồi biến mất (~1.3 giây)."""
        # Mỗi ký hiệu một cửa sổ trong suốt riêng đè lên nhân vật: đặt nhãn chung cửa sổ thì chỗ màu khoá quanh ký hiệu
        # "đục thủng" luôn cả nhân vật, lộ màn hình phía sau thành ô vuông trắng/đen.
        if lab is None:
            win = tk.Toplevel(root)
            win.withdraw()
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            win.attributes("-transparentcolor", KEY)
            lab = tk.Label(win, bg=KEY, bd=0)
            lab.pack()
            win.update_idletasks()
            u, h = ctypes.windll.user32, ctypes.c_void_p(int(win.wm_frame(), 16))
            u.SetWindowLongW(h, -20, u.GetWindowLongW(h, -20) | 0x08000020)  # không cướp focus, chuột bấm xuyên qua
        win, t = lab.winfo_toplevel(), step / 40
        if t >= 1 or hidden.is_set():
            return win.destroy()
        img = glyphs[kind][int(t * len(glyphs[kind]))]
        lab.config(image=img)
        cx, cy = root.winfo_rootx() + x + 6 * math.sin(t * 7), root.winfo_rooty() + y - 50 * t
        win.geometry(f"+{round(cx - img.width() / 2)}+{round(cy - img.height() / 2)}")
        win.deiconify()
        win.lift()  # nổi trên nhân vật kể cả khi nhân vật vừa tự giành lại "trên cùng"
        root.after(33, puff, kind, x, y, step + 1, lab)

    def burst(kind, n):
        """n ký hiệu bay ra quanh đầu nhân vật, cách nhau 0.15s: Z bên phải đầu, ! hai bên, ♥ ngẫu nhiên hai bên."""
        y = H - SIZE + {"z": 60, "heart": 90, "bang": 40}[kind]
        for i in range(n):
            side = 1 if kind == "z" else (-1) ** i if kind == "bang" else random.choice((-1, 1))
            root.after(150 * i, puff, kind, W // 2 + side * random.randint(60, 95), y + random.randint(-10, 10))

    zz = [None]  # vòng Z đang chạy (chỉ một vòng, kẻo ngủ-dậy-ngủ nhanh thì Z bay gấp đôi)

    def zzz():
        """Đang ngủ: cứ 1.6 giây một chữ Z bay lên cạnh đầu."""
        if sleeping.is_set():
            if not hidden.is_set():
                burst("z", 1)
            zz[0] = root.after(1600, zzz)
        else:
            zz[0] = None

    last_said = [time.time()]

    def say(line, emote):
        stop_walk()  # đang đi dạo mà có chuyện để nói thì đứng lại nói
        last_said[0] = time.time()
        cur["emote"] = emote
        look()  # emote mới có thể nghiêng phía khác: tính lại hướng lật ngay, khỏi chớp sai 1 khung
        if hop[0]:  # đang chuyển động dở mà có câu mới thì làm lại từ đầu
            root.after_cancel(hop[0])
        animate(motion(emote))
        show_bubble(line)
        if emote == "soc":
            burst("bang", 2)

    out, paused, asks, seen = queue.Queue(), threading.Event(), queue.Queue(), {"title": ""}
    sleeping = threading.Event()
    rest = {"start": time.time(), "next_tired": TIRED_HOURS * 3600, "night": None, "greeted": None}

    def greet():
        """Chào một lần mỗi ngày: dịp đặc biệt (sinh nhật, Tết, Trung thu, thứ Hai/Sáu) hoặc chào theo giờ."""
        memory, hour, today = load_memory(), time.localtime().tm_hour, date.today()
        special = special_day(today, hour, memory, name_from(memory))
        line, emote = special or greeting(hour, name_from(memory))
        rest["greeted"] = today
        if not special and hour in NIGHT_HOURS:  # câu chào đã nhắc khuya rồi, đêm nay khỏi nhắc lại
            rest["night"] = today.isoformat()
        say(line, emote)
        if special:
            burst("heart", 5)

    def check_rest():
        """Rời máy quá AWAY_MINUTES: ngủ gục, ngừng chụp. Quay lại: tỉnh dậy. Ngồi lâu / quá nửa đêm: buồn ngủ, nhắc nghỉ.
        Đang gõ câu hỏi thì không nói gì, kẻo bong bóng che ô nhập."""
        idle, now = idle_seconds(), time.time()
        # xem video / chơi game toàn màn hình thì không chạm chuột vẫn là đang dùng máy
        if idle >= AWAY_MINUTES * 60 and not fullscreen():
            if not sleeping.is_set():
                sleeping.set()
                if not entry.winfo_ismapped():
                    say(pick("away"), "buon_ngu")
                if zz[0] is None:
                    zzz()
        elif sleeping.is_set():
            sleeping.clear()
            rest.update(start=now - idle, next_tired=TIRED_HOURS * 3600)  # rời máy đủ lâu: đếm giờ ngồi lại từ đầu
            if not entry.winfo_ismapped():
                if rest["greeted"] != date.today():  # qua ngày mới (để máy qua đêm): chào ngày mới thay cho "về rồi"
                    greet()
                else:
                    say(pick("back"), "lap_lanh")
        elif not entry.winfo_ismapped():
            used, today = now - rest["start"], time.strftime("%Y-%m-%d")
            if used >= rest["next_tired"]:
                rest.update(next_tired=used + 3600, night=today)  # nhắc một câu thôi, không nhắc đêm khuya ngay sau
                say(pick("tired", h=int(used // 3600)), "buon_ngu")
            elif time.localtime().tm_hour in NIGHT_HOURS and rest["night"] != today:
                rest.update(night=today, next_tired=max(rest["next_tired"], used + 3600))
                say(pick("night"), "buon_ngu")
        root.after(2000, check_rest)

    def stroll(dx, steps, i=0):
        """Nhảy lò cò ngang: mỗi bước 16 khung (~0.26s) bật lên 8px, cửa sổ trượt đều theo; xong thì ngồi yên chỗ mới."""
        if i >= steps * 16:
            return stop_walk()
        root.geometry(f"+{round(walk['x0'] + dx * (i + 1) / (steps * 16))}+{root.winfo_y()}")
        face.place_configure(y=-round(8 * math.sin(math.pi * (i % 16) / 16)))
        walk["job"] = root.after(16, stroll, dx, steps, i + 1)

    def stop_walk():  # đi tới nơi, hoặc bị ngắt giữa chừng (có câu mới, bị kéo, bị ẩn, tắt đi dạo)
        if walk["job"]:
            root.after_cancel(walk["job"])
        walk.update(dir=None, job=None)
        face.place_configure(y=0)

    def start_walk():
        """Đi 120-320px sang trái hoặc phải, không ra khỏi màn hình; chỉ đi ngang nên đang ngồi trên taskbar thì vẫn ở đó.
        Không lưu vị trí mới: mở lại chương trình thì về chỗ bạn đã kéo."""
        x, lo, hi = root.winfo_x(), work[0], work[2] - W
        d = random.choice((-1, 1)) * random.randint(120, 320)
        d = max(lo, min(hi, x + (d if lo <= x + d <= hi else -d))) - x  # đụng mép thì quay đầu đi hướng kia
        if abs(d) >= 40:
            walk.update(dir="right" if d > 0 else "left", x0=x)
            cur["emote"] = random.choice(["mim_cuoi", "le_luoi", "lap_lanh"])
            look()
            render()
            stroll(d, max(3, abs(d) // 40))

    def pointer_on_me():  # chuột đang ở trên nhân vật: có thể sắp bấm, đừng chạy mất
        px, py = root.winfo_pointerxy()
        return 0 <= px - root.winfo_rootx() < W and 0 <= py - root.winfo_rooty() < H

    def idle_pose():
        """Im lặng lâu thì tự đổi dáng hoặc đi dạo (không nói) cho đỡ đứng im như tượng; đang ngủ thì để yên."""
        if (time.time() - last_said[0] > IDLE_POSE_SECONDS and not walk["job"]
                and not (sleeping.is_set() or hidden.is_set() or entry.winfo_ismapped())):
            if walk["on"] and random.random() < WALK_CHANCE and not pointer_on_me():
                start_walk()
            else:
                cur["emote"] = random.choice([e for e in IDLE_POSES if e != cur["emote"]])
                look()
                render()
            last_said[0] = time.time() - random.randint(0, IDLE_POSE_SECONDS // 2)  # lần sau lệch chút cho tự nhiên
        root.after(5000, idle_pose)

    pat = {"x": None, "dir": 0, "flips": [], "until": 0.0}

    def stroke(e):
        """Xoa đầu: rê chuột qua lại (mỗi lần ≥12px) trên nửa trên nhân vật, đổi chiều 4 lần trong 1.5s thì nhột."""
        if e.y > face.winfo_height() * 0.45:
            pat["x"] = None
            return
        if pat["x"] is not None and abs(e.x - pat["x"]) < 12:  # rung tay vài px không tính
            return
        d = 0 if pat["x"] is None else (1 if e.x > pat["x"] else -1)
        pat["x"] = e.x
        if d and d != pat["dir"]:
            pat["dir"], now = d, time.time()
            pat["flips"] = [t for t in pat["flips"] if now - t < 1.5] + [now]
            if len(pat["flips"]) >= 4 and now > pat["until"] and not entry.winfo_ismapped():
                pat.update(flips=[], until=now + 10)  # nhột xong nghỉ 10s mới nhột tiếp
                say(pick("pat"), "de_thuong")
                burst("heart", 4)

    power = {"low": False, "online": True}

    def check_system():
        """Pin dưới LOW_BATTERY% mà không cắm sạc: nhắc một lần (cắm sạc / pin lên lại thì reset). Mất mạng / có lại mạng."""
        percent, plugged = battery()
        if percent is not None and percent < LOW_BATTERY and not plugged:
            if not power["low"] and not entry.winfo_ismapped():
                power["low"] = True
                say(pick("battery", p=percent), "soc")
        elif plugged or (percent or 0) >= LOW_BATTERY + 5:
            power["low"] = False
        net = online()
        if net != power["online"] and not entry.winfo_ismapped():
            power["online"] = net
            say(*((pick("net_back"), "lap_lanh") if net else (pick("net_lost"), "buon")))
        root.after(30000, check_system)

    app = {"cat": None, "at": {}}  # loại app đang mở, lần cuối phản ứng với từng loại

    def track():
        """Nhớ tiêu đề cửa sổ khác gần nhất (lúc người dùng bấm vào nhân vật thì nó mới là cửa sổ cần xét riêng tư),
        và phản ứng ngay khi chuyển sang code / game / chat: mỗi loại 10 phút tối đa 1 lần, không chen ngang câu
        vừa nói (20 giây), không nói khi đang tạm dừng (đã hứa không nhìn), ngủ, ẩn, gõ câu hỏi hay ở cửa sổ riêng tư."""
        title = active_title()
        if title != TITLE:
            seen["title"] = title
            cat, now = app_category(title, fullscreen()), time.time()
            if cat != app["cat"]:
                app["cat"] = cat
                quiet = (paused.is_set() or sleeping.is_set() or hidden.is_set() or entry.winfo_ismapped()
                         or is_private(title) or now - last_said[0] < APP_QUIET_SECONDS)
                if cat and not quiet and now - app["at"].get(cat, 0) > APP_COOLDOWN_MINUTES * 60:
                    app["at"][cat] = now
                    say(pick(cat), APP_EMOTES[cat])
        root.after(500, track)

    entry = tk.Entry(root, font=("Segoe UI", 11), fg="#5b3442", bg="#fff8fb", insertbackground="#5b3442",
                     relief="flat", highlightthickness=2, highlightbackground="#f08aa0", highlightcolor="#f08aa0")

    def open_ask(_):
        if click_job[0]:  # cú bấm đầu của bấm đúp: không tính là tạm dừng
            root.after_cancel(click_job[0])
            click_job[0] = None
        show_bubble(pick("ask_hint"), y=ABOVE_ENTRY)
        entry.delete(0, "end")
        entry.place(relx=0.5, y=H - SIZE + 4, anchor="s", width=W - 24, height=34)
        root.focus_force()  # cửa sổ không viền phải giành focus thì mới gõ được
        entry.focus_set()

    def send_ask(_):
        question = entry.get().strip()
        entry.place_forget()
        if question:
            asks.put(question)
            say(pick("thinking"), "suy_tu")
        else:
            bubble.place_forget()

    def cancel_ask(_):
        entry.place_forget()
        bubble.place_forget()

    entry.bind("<Return>", send_ask)
    entry.bind("<Escape>", cancel_ask)

    def toggle(_):
        if paused.is_set():
            paused.clear()
            say(pick("resume"), "lap_lanh")
        else:
            paused.set()
            say(pick("pause"), "xau_ho")
        tray.update_menu()  # pystray dựng menu Windows một lần rồi giữ nguyên: phải dựng lại thì dấu tích mới đổi

    todo, hidden = queue.Queue(), threading.Event()  # todo: việc menu khay nhờ làm, chạy ở luồng giao diện

    def show_hide():
        if hidden.is_set():
            hidden.clear()
            root.deiconify()
        else:  # ẩn xuống khay: không hiện, không chụp màn hình
            stop_walk()
            hidden.set()
            entry.place_forget()
            root.withdraw()

    def tray_ask():
        if hidden.is_set():
            show_hide()
        open_ask(None)

    def open_memory():
        if not MEMORY_FILE.exists():
            MEMORY_FILE.write_text(MEMORY_HEADER, encoding="utf-8")
        os.startfile(MEMORY_FILE)  # mở bằng Notepad (chương trình mặc định cho .txt)

    def reset_position():  # lỡ kéo nhân vật ra khuất màn hình thì gọi về
        POS_FILE.unlink(missing_ok=True)
        root.geometry(f"+{work[2] - W}+{work[3] - H}")

    def ask_clipboard():
        """Gửi đoạn chữ đang có trong clipboard (người dùng vừa Ctrl+C) cho model giải thích / dịch."""
        try:
            clip = root.clipboard_get().strip()
        except tk.TclError:  # clipboard trống hoặc đang chứa ảnh, file...
            clip = ""
        if hidden.is_set():
            show_hide()
        entry.place_forget()
        if not clip:
            return say(pick("clip_empty"), "suy_tu")
        asks.put(("clip", clip[:CLIP_MAX]))
        say(pick("clip_read"), "mot_sach")

    def fire_reminder(what):
        if entry.winfo_ismapped():  # đang gõ câu hỏi thì đợi chút, kẻo che ô nhập
            return root.after(5000, fire_reminder, what)
        if hidden.is_set():  # nhắc việc thì hiện lên dù đang ẩn
            show_hide()
        say(pick("reminder", what=what), "lap_lanh")

    focus = {"until": 0.0, "break_until": 0.0, "nag": 0.0, "left": None, "minutes": FOCUS_MINUTES}

    def start_focus(minutes, announce=True):
        """Bắt đầu (hoặc bắt đầu lại) một phiên tập trung. Từ câu nói với nhân vật thì câu trả lời đã báo rồi, khỏi nói thêm."""
        focus.update(until=time.time() + minutes * 60, break_until=0.0, left=None, minutes=minutes)
        if announce:
            say(pick("focus_start", m=minutes), "co_vu")
        tray.update_menu()

    def focus_toggle():
        if focus["until"]:
            focus["until"] = 0.0
            say(pick("focus_stop"), "mim_cuoi")
            tray.update_menu()
        else:
            start_focus(FOCUS_MINUTES)

    def focus_label(_):
        if not focus["until"]:
            return f"Tập trung {FOCUS_MINUTES} phút"
        return f"Dừng tập trung (còn {max(1, math.ceil((focus['until'] - time.time()) / 60))} phút)"

    def check_focus():
        """Hết giờ tập trung: khen + nhắc nghỉ. Đang tập trung mà mở trang trong FOCUS_BLOCK: dỗi (mỗi phút tối đa 1 lần).
        Hết giờ nghỉ: gọi quay lại. Đang gõ câu hỏi thì để lượt sau."""
        now = time.time()
        if not entry.winfo_ismapped():
            if focus["until"] and now >= focus["until"]:
                focus.update(until=0.0, break_until=now + BREAK_MINUTES * 60)
                say(pick("focus_done", m=focus["minutes"], b=BREAK_MINUTES), "nhay_mat_ok")
                tray.update_menu()
            elif focus["until"]:
                title = active_title()
                title = seen["title"] if title == TITLE else title
                if any(w in title.lower() for w in FOCUS_BLOCK) and now - focus["nag"] > 60:
                    focus["nag"] = now
                    say(pick("focus_nag"), "gian_doi")
                left = math.ceil((focus["until"] - now) / 60)
                if left != focus["left"]:  # menu không tự đổi chữ: dựng lại mỗi phút cho "còn N phút" đúng
                    focus["left"] = left
                    tray.update_menu()
            elif focus["break_until"] and now >= focus["break_until"]:
                focus["break_until"] = 0.0
                say(pick("break_done"), "co_vu")
        root.after(2000, check_focus)

    def toggle_walk():  # tắt chỉ tới khi thoát chương trình; muốn tắt hẳn thì sửa WALK = False ở đầu file
        walk["on"] = not walk["on"]
        if not walk["on"]:
            stop_walk()
        tray.update_menu()

    def item(text, job, **kw):  # pystray gọi từ luồng riêng của nó: chỉ xếp việc, poll() làm giùm
        return pystray.MenuItem(text, lambda: todo.put(job), **kw)

    tray = pystray.Icon("tro_ly_man_hinh", Image.open(EMOTE_DIR / "mim_cuoi.png").resize((64, 64)), TITLE, pystray.Menu(
        item("Hiện / ẩn nhân vật", show_hide, default=True),  # bấm trái vào icon = mục này
        item("Hỏi nhân vật...", tray_ask),
        item("Hỏi về đoạn vừa copy", ask_clipboard),
        item(focus_label, focus_toggle),
        item("Tạm dừng nhìn màn hình", lambda: toggle(None), checked=lambda _: paused.is_set()),
        item("Cho đi dạo khi rảnh", toggle_walk, checked=lambda _: walk["on"]),
        item("Mở file ký ức", open_memory),
        item("Về góc mặc định", reset_position),
        pystray.Menu.SEPARATOR,
        item("Thoát", root.destroy),
    ))

    def poll():
        while not todo.empty():
            todo.get()()
        while not out.empty():
            line, emote, *answer = out.get()  # answer = [True, nhắc, tập trung] nếu là câu trả lời
            # bỏ câu bình luận về lúc đang tạm dừng hoặc đang gõ câu hỏi (kẻo che ô nhập); câu trả lời thì luôn hiện
            if answer or not (paused.is_set() or entry.winfo_ismapped()):
                say(line, emote)
                if not MOCK:  # mock chọn emote ngẫu nhiên, ghi vào chỉ làm rối nhật ký
                    log_line("trả lời" if answer else "bình luận", emote, line)
            if answer and answer[1]:  # hẹn giờ ở luồng giao diện; tắt chương trình thì mất lời nhắc
                minutes, what = answer[1]
                root.after(minutes * 60000, fire_reminder, what)
            if answer and answer[2]:  # "mình code 40 phút nha" -> bật chế độ tập trung đúng 40 phút
                start_focus(answer[2], announce=False)
        root.after(200, poll)

    drag, click_job = {}, [None]

    def press(e):
        stop_walk()  # bị nhấc lên kéo thì thôi đi dạo
        drag.update(x=e.x_root, y=e.y_root, wx=root.winfo_x(), wy=root.winfo_y(), moved=False)

    def move(e):
        if "x" not in drag:  # giữ chuột từ chỗ khác rồi rê vào nhân vật: không phải kéo nhân vật
            return
        dx, dy = e.x_root - drag["x"], e.y_root - drag["y"]
        drag["moved"] = drag["moved"] or abs(dx) + abs(dy) > 5  # rung tay vài px vẫn tính là bấm
        if drag["moved"]:
            if "prev" not in drag:  # vừa bắt đầu bị nhấc lên: đổi sang ảnh bị xách cổ áo, nhớ emote cũ để thả ra thì đổi lại
                drag["prev"] = cur["emote"]
                if hop[0]:
                    root.after_cancel(hop[0])
                    hop[0] = None
                face.place_configure(x=0, y=0)
                cur.update(emote=DRAG_EMOTE, turn=False)
                look()
                render()
                show_bubble(pick("dragged"))
            drag["pos"] = f"{drag['wx'] + dx} {drag['wy'] + dy}"
            root.geometry("+" + drag["pos"].replace(" ", "+"))

    def release(e):
        state = dict(drag)
        drag.clear()  # mỗi lần nhấn chỉ dùng một lần
        # nhả chuột mà trước đó không nhấn trên nhân vật (nhân vật đi dạo trượt tới dưới con trỏ),
        # hoặc nhả của cú bấm đúp (lần nhấn thứ 2 chỉ gọi open_ask, không qua press): bỏ qua
        if "moved" not in state:
            return
        if state["moved"]:
            # lưu toạ độ vừa tính, không đọc winfo_x(): Tk chưa kịp dời cửa sổ nên nó còn trả chỗ cũ
            POS_FILE.write_text(state["pos"])
            say(pick("dropped"), state["prev"])  # đáp xuống: về emote cũ, nhún một cái
        else:
            # chờ hết thời gian bấm đúp của Windows (mặc định 500ms) rồi mới tạm dừng, kẻo bấm đúp chậm bị tính là bấm đơn
            click_job[0] = root.after(ctypes.windll.user32.GetDoubleClickTime(), toggle, e)

    face.bind("<ButtonPress-1>", press)
    face.bind("<B1-Motion>", move)
    face.bind("<ButtonRelease-1>", release)
    face.bind("<Double-Button-1>", open_ask)
    face.bind("<Motion>", stroke)  # chỉ nhận khi KHÔNG giữ chuột; giữ chuột trái kéo thì <B1-Motion> lo
    def stay_on_top():
        # game toàn màn hình kiểu borderless cũng tự lên topmost và đè mình, nên cứ 2s giành lại;
        # 0x13 = không dời, không đổi cỡ, không cướp focus của game. Game exclusive fullscreen thì không đè được.
        # c_void_p(-1) = HWND_TOPMOST; truyền -1 trần thì ctypes cắt còn 32 bit và Windows bỏ qua
        ctypes.windll.user32.SetWindowPos(ctypes.c_void_p(int(root.wm_frame(), 16)), ctypes.c_void_p(-1), 0, 0, 0, 0, 0x13)
        root.after(2000, stay_on_top)

    face.bind("<Button-3>", lambda _: show_hide())  # chuột phải: ẩn xuống khay; thoát hẳn thì dùng menu khay
    root.after(1000, stay_on_top)
    breathe()
    follow_mouse()
    track()
    threading.Thread(target=worker, args=(out, paused, asks, seen, sleeping, hidden), daemon=True).start()
    greet()
    root.after(20000, check_rest)  # để câu chào hiện đủ rồi mới xét buồn ngủ (mở máy lúc nửa đêm)
    root.after(20000, check_system)
    root.after(5000, idle_pose)
    root.after(2000, check_focus)
    poll()
    tray.run_detached()
    try:
        root.mainloop()
    finally:
        tray.stop()  # thoát bằng chuột phải hay menu khay đều gỡ icon, không để icon ma lại trên taskbar


if __name__ == "__main__":
    # Chỉ chạy một bản: bấm shortcut khi bản tự chạy lúc bật máy đang chạy thì báo, khỏi mở nhân vật thứ hai chồng lên.
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = ctypes.c_void_p
    single = k32.CreateMutexW(None, False, "TroLyManHinh_ClaudeChan")  # giữ tới khi thoát chương trình
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(None, "Claude-chan đang chạy rồi nè!\nBấm icon ở khay hệ thống (cạnh đồng hồ) để hiện.",
                                         TITLE, 0x40)
        sys.exit()
    main()
