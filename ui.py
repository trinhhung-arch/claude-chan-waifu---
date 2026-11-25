"""Giao diện nhân vật: cửa sổ trong suốt, bong bóng, chuyển động, chuột, menu khay, hẹn giờ."""
import ctypes
import math
import os
import queue
import random
import sys
import threading
import time
import tkinter as tk
from datetime import date
from pathlib import Path

import pystray
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk

from config import APP_COOLDOWN_MINUTES, APP_EMOTES, APP_QUIET_SECONDS, AWAY_MINUTES, BREAK_MINUTES, BUBBLE_SECONDS, CLIP_MAX, DRAG_EMOTE, EMOTES, EMOTE_DIR, FACING, FOCUS_BLOCK, FOCUS_MINUTES, IDLE_POSES, IDLE_POSE_SECONDS, KEY, LOW_BATTERY, MEMORY_FILE, MEMORY_HEADER, MOCK, NIGHT_HOURS, POS_FILE, SIZE, TIRED_HOURS, TITLE, WALK, WALK_CHANCE
from dialogue import app_category, greeting, name_from, pick, special_day
from memory import load_memory, log_line
from desktop import active_title, battery, fullscreen, idle_seconds, is_private, online
from brain import worker

HEART_IMG = Image.open(Path(__file__).parent / "tim_pixel.png").convert("RGBA")  # tim pixel bay ra khi được xoa đầu


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
