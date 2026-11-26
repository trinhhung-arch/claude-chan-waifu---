"""Cửa sổ nhân vật: vẽ emote, thở, quay theo chuột, bong bóng chia trang, đang nghĩ, chuyển động, ký hiệu bay,
đi dạo, kéo thả, xoa đầu, ô hỏi, ẩn/hiện."""
import ctypes
import math
import random
import time
import tkinter as tk

from ..core.config import BLINK, BUBBLE_SECONDS, DROWSY, PUFF_EMOTE, DIZZY_EMOTE, DRAG_EMOTE, EMOTES, FACING, KEY, POS_FILE, SIZE, THINK_EMOTE, TITLE, WALK
from ..desktop import window_rect, windows
from ..dialogue import pick
from ._art import (BREATH, SWING_MAX, SWING_STEP, dot_frames, emote_frames, glyph_frames, hand_images, overlay, peek_frame,
                   squash_frame,
                   swing_frames)
from ._motion import RUB_WINDOW, SPIN_WINDOW, motion, rubbed, spun

W, H = 340, SIZE + 170  # 170px phía trên đủ cho bong bóng 4 dòng
# Nền bong bóng / ô hỏi là màu khoá: đè lên chỗ nào là "đục" mất tóc chỗ đó thành một đường cắt ngang. Nên bong bóng
# đứng sát trên đỉnh đầu lúc hít vào, và nảy lên theo nhân vật khi nhảy (cao nhất JUMP px, chừa sẵn chỗ phía trên).
PET_SEQ = "aaabbcdd"  # dáng tay từng khung (30 khung/giây) đúng nhịp video petpet: nắm ấn, nhấc, xoè thấp, xoè
# đặt tay như meme petpet: tay nắm úp lòng bàn tay che phần trên đầu; tay xoè thì đầu nằm gọn trong khe giữa ngón cái và
# các ngón, bị ép bẹp dí; đầu ngón tay ở mép phải đầu
PET_SQUASH = {"a": 0.15, "b": 0.05, "c": 0.5, "d": 0.4}  # đầu bẹp bao nhiêu ở mỗi dáng tay
PET_HAND_Y = {"a": 92, "b": 78, "c": 93, "d": 96}  # góc trên tay cao hơn đỉnh đầu (đang bẹp) bao nhiêu px
PET_HAND_X = -40  # góc trái tay so với mép trái hình nhân vật
REST_Y = H - SIZE - BREATH  # đáy bong bóng lúc đứng yên
JUMP = round(max(max(p[1] for p in motion(e)) for e in EMOTES))
LOOP_WHILE_TALKING = {"co_vu"}  # emote nhảy múa lặp lại suốt lúc bong bóng còn hiện, không chỉ một lượt
PEEK_HEAD, PEEK_SHOW = 125, 0.85  # lúc núp: chỉ ló phần đầu cao 125px (tới ngang mũi), bề ngang lộ 85% (thấy đủ mặt)
SIDE_HEAD = 115  # kiểu núp thò đầu ngang từ mép trái / phải / treo ngược ở mép trên: phần đầu thò vào chừng này px
THROW_SPEED, THROW_MAX = 900, 4500  # thả tay lúc đang vung nhanh hơn chừng này px/giây thì bay theo đà (tối đa)
THROW_FRICTION, THROW_BOUNCE = 2.6, 0.6  # bay chậm dần (càng lớn càng mau dừng); nảy ở rìa giữ lại 60% tốc độ
# nhún (ngang, dọc) từng khung 40ms: đáp / va rìa trên-dưới thì bẹp xuống rồi bật lại, va rìa trái-phải thì ép ngang
BUMPS = {"land": [(1.16, 0.82), (1.1, 0.9), (0.96, 1.05), (1.02, 0.99), (1.0, 1.0)],
         "side": [(0.86, 1.08), (0.93, 1.04), (1.0, 1.0)]}
DIZZY_PATH = [(round(8 * math.sin(i * 0.33) * (1 - i / 150)), 0, 0) for i in range(150)] + [(0, 0, 0)]  # lảo đảo ~2.4s
ENTRY_Y = H - SIZE - BREATH  # đáy ô hỏi: sát trên đầu lúc đứng yên (lúc nhảy tóc chui dưới ô một chút, ô không đục)
ABOVE_ENTRY = ENTRY_Y - 34  # đáy bong bóng khi ô hỏi đang mở: nằm trên ô hỏi


class Character:
    """state: trạng thái chung (tạm dừng, ngủ, ẩn). Gán on_click (bấm đơn) và on_ask(câu hỏi) trước khi chạy."""

    def __init__(self, state):
        self.state = state
        self.on_click = self.on_ask = lambda *_: None
        root = self.root = tk.Tk()
        root.title(TITLE)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", KEY)
        root.config(bg=KEY)
        work = self.work = (ctypes.c_long * 4)()  # vùng làm việc = màn hình trừ taskbar (trái, trên, phải, dưới)
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

        self.pics, self.glyphs, (self.dots, self.dots_left) = emote_frames(), glyph_frames(), dot_frames()
        self.dot_n = 0  # khung ba chấm đang hiện
        self.swing_pics = swing_frames(DRAG_EMOTE)  # bị xách cổ áo: lắc qua lắc lại theo tay kéo
        self.swing = {"a": 0.0, "v": 0.0, "x": None, "vx": 0.0, "t": None}  # góc (độ), tốc độ góc, x cửa sổ / tốc độ khung trước
        # emote đang hiện, khung thở, lật theo chuột, quay ngoắt (dỗi)
        self.cur = {"emote": "mim_cuoi", "k": 0, "mouse_flip": False, "turn": False, "mouse_side": None}
        self.walk = {"on": WALK, "dir": None, "job": None, "x0": 0}  # đi dạo: bật/tắt, hướng, vòng hẹn giờ, x xuất phát
        self.face = tk.Label(root, image=self.pics["mim_cuoi", False][0], bg=KEY, bd=0, cursor="hand2")
        self.face.place(relx=0.5, rely=1, anchor="s")  # cùng trục giữa với bong bóng
        self.bubble = tk.Canvas(root, bg=KEY, highlightthickness=0)
        self.entry = tk.Entry(root, font=("Segoe UI", 11), fg="#5b3442", bg="#fff8fb", insertbackground="#5b3442",
                              relief="flat", highlightthickness=2, highlightbackground="#f08aa0",
                              highlightcolor="#f08aa0")
        self.hide_job = self.typing = self.on_typed = self.hop = self.zz = self.click_job = None
        self.bubble_y = REST_Y
        self.explaining = False  # đang hiện câu trả lời cho câu người dùng hỏi
        self.paging = None  # (pages, i, y) của trang kế tiếp khi trang đang hiện có ▼
        # số câu hỏi đang chờ model trả lời (model to có khi nghĩ 20-50 giây): trong lúc đó giữ dáng suy nghĩ + bong bóng,
        # không tự đổi dáng, đi dạo, phản ứng app hay nhắc nhở, kẻo trông như quên mất là đang nghĩ
        self.waiting, self.think_line, self.head_dots = 0, "", None
        self.last_said = time.time()
        self.drag, self.pat = {}, {"xs": [], "last": 0.0, "xy": None}
        self.squash_img = self.bump_job = None  # ảnh bẹp / giãn đang hiện (nhún khi đáp, va rìa)
        self.dizzy_until = 0.0  # chóng mặt sau khi bị quăng: tới lúc này nhấc lên thì kêu đừng quăng
        self.dance_until = 0.0  # đang nhún theo nhạc tới lúc này
        self.playing = False  # đang chơi mini game: đừng tự đi dạo / núp / đổi dáng
        self.hand, self.hand_imgs, self.pet_job = None, hand_images(), None  # bàn tay xoa đầu (cửa sổ riêng), 4 dáng tay
        self.blinking = False  # đang nhắm mắt trong một cái chớp
        self.peek = None  # đang núp ở góc dưới rìa màn hình: {"home": (x, y) chỗ cũ, "until": lúc tự đi ra}
        self.peek_depth = 0  # đang thụt hình xuống bao nhiêu px (núp sau taskbar, chỉ ló đầu)
        self.peek_img = None  # ảnh xoay ngang đang hiện (núp thò đầu từ mép trái / phải)
        self.perch = None  # đang đứng trên mép trên một cửa sổ: {"hwnd": cửa sổ, "dx": x mình - mép trái cửa sổ}
        self.air_job = None  # đang nhảy lên / rơi xuống (câu nói chen vào không được cắt ngang, kẻo kẹt giữa trời)

        self.bubble.bind("<Button-1>", self._next_page)
        self.entry.bind("<Return>", self._send_ask)
        self.entry.bind("<Escape>", lambda _: self.close_ask(bubble=True))
        f = self.face
        f.bind("<ButtonPress-1>", self._press)
        f.bind("<B1-Motion>", self._move)
        f.bind("<ButtonRelease-1>", self._release)
        f.bind("<Double-Button-1>", lambda _: self.open_ask())
        f.bind("<Motion>", self._stroke)  # chỉ nhận khi KHÔNG giữ chuột; giữ chuột trái kéo thì <B1-Motion> lo
        f.bind("<Button-3>", lambda _: self.show_hide())  # chuột phải: ẩn xuống khay; thoát hẳn thì dùng menu khay

    # ---- những gì module khác hỏi ----
    @property
    def talking(self):  # bong bóng đang hiện (đang nói, chưa đọc xong)
        return bool(self.bubble.winfo_ismapped())

    @property
    def asking(self):  # đang mở ô hỏi: đừng nói gì, kẻo bong bóng che chỗ gõ
        return bool(self.entry.winfo_ismapped())

    @property
    def petting(self):  # đang được xoa đầu: đứng yên cho xoa, đừng tự đi dạo / đổi dáng / nhảy nhót
        return self.pet_job is not None

    @property
    def thinking(self):
        return self.waiting > 0

    @property
    def answering(self):  # đang nghĩ hoặc đang giải thích câu người dùng hỏi: chưa nhận câu hỏi mới, bấm không che mắt
        return self.waiting > 0 or (self.explaining and bool(self.bubble.winfo_ismapped()))

    def start(self):
        """Bắt đầu thở, chớp mắt, quay theo chuột, giành lại trên cùng."""
        self._breathe()
        self._blink()
        self._follow_mouse()
        self.root.after(1000, self._stay_on_top)

    # ---- vẽ ----
    def _render(self):
        """Vẽ lại nhân vật theo cur; ảnh không đổi thì thôi (gọi 60 lần/giây lúc chuyển động vẫn nhẹ)."""
        c = self.cur
        if self.squash_img:
            img = self.squash_img
        elif self.peek_img:
            img = self.peek_img
        elif c["emote"] == DRAG_EMOTE and "prev" in self.drag:  # đang bị kéo: ảnh nghiêng theo góc lắc
            shown = SWING_MAX * math.tanh(self.swing["a"] / SWING_MAX)  # gần giới hạn thì chậm dần, khỏi khựng cứng
            img = self.swing_pics[round(shown / SWING_STEP) * SWING_STEP]
        else:
            emote = BLINK[c["emote"]] if self.blinking and c["emote"] in BLINK else c["emote"]
            img = self.pics[emote, c["mouse_flip"] != c["turn"]][c["k"]]
        if self.face.cget("image") != str(img):
            self.face.config(image=img)

    def _look(self):
        """Quay mặt theo chuột: emote đang nghiêng một phía (FACING) thì lật cho mặt hướng về con trỏ.
        Chuột ngay giữa nhân vật (±15px) thì giữ phía cũ, khỏi lật qua lật lại khi chuột đứng yên đúng chính giữa."""
        c, root = self.cur, self.root
        dx = root.winfo_pointerx() - (root.winfo_rootx() + W // 2)
        if abs(dx) > 15:
            c["mouse_side"] = "left" if dx < 0 else "right"
        # Tính lại từ phía chuột đã nhớ cho MỖI emote: emote mới có thể vốn nghiêng phía khác emote cũ, nên không được
        # giữ nguyên trạng thái lật cũ (chuột đang ở gần giữa lúc vừa xoa đầu / bấm / thả ra thì sẽ quay ngược).
        side, want = FACING.get(c["emote"]), self.walk["dir"] or c["mouse_side"]  # đang đi dạo: nhìn hướng đi
        c["mouse_flip"] = bool(side and want and side != want)

    def _face_for(self, emote):
        """Đang được xoa đầu thì giữ nguyên mặt phê (trừ lúc bị nhấc lên kéo đi): lời nhắc, bình luận, nói xong về
        mặt thường... đều không được đổi hình giữa chừng; câu nói vẫn hiện bình thường."""
        return PUFF_EMOTE if self.petting and "prev" not in self.drag else emote

    def pose(self, emote):
        """Đổi dáng không nói gì."""
        self.cur["emote"] = self._face_for(emote)
        self._look()
        self._render()

    def _follow_mouse(self):
        self._look()
        self._render()
        if self.head_dots and "prev" not in self.drag:  # vừa quay sang phía kia: ba chấm đổi bên ngay, khỏi chờ 0.4s
            self._place_dots()
        self.root.after(40, self._follow_mouse)  # 25 lần/giây: rê chuột nhanh vẫn theo kịp; chỉ đổi ảnh khi hướng đổi

    def _breathe(self):
        """Hít vào thở ra một nhịp mỗi 3.5 giây."""
        self.cur["k"] = round(BREATH * (1 - math.cos(2 * math.pi * time.perf_counter() / 3.5)) / 2)
        self._render()
        self.root.after(50, self._breathe)

    def _blink(self, step=0):
        """Chớp mắt ngẫu nhiên mỗi 2.5-6 giây (chỉ emote có ảnh nhắm mắt trong BLINK): nhắm ~0.12s rồi mở;
        thỉnh thoảng chớp đôi. Emote buồn ngủ (DROWSY) thì díp mắt: nhắm lâu, lờ đờ mở ra một lúc, lại díp."""
        if step == 0 and self.cur["emote"] in DROWSY:
            self.blinking = True
            self._render()
            return self.root.after(random.randint(900, 1400), self._blink, "drowsy")
        if step == "drowsy":
            self.blinking = False
            self._render()
            return self.root.after(random.randint(1200, 2000), self._blink)
        if step == 0:
            if self.cur["emote"] in BLINK:
                self.blinking = True
                self._render()
                return self.root.after(120, self._blink, 1)
        elif step == 1:
            self.blinking = False
            self._render()
            if random.random() < 0.2:  # chớp đôi
                return self.root.after(140, self._blink, 2)
        elif step == 2:
            self.blinking = True
            self._render()
            return self.root.after(110, self._blink, 3)
        else:
            self.blinking = False
            self._render()
        self.root.after(random.randint(2500, 6000), self._blink)

    def _stay_on_top(self):
        # game toàn màn hình kiểu borderless cũng tự lên topmost và đè mình, nên cứ 2s giành lại;
        # 0x13 = không dời, không đổi cỡ, không cướp focus của game. Game exclusive fullscreen thì không đè được.
        # c_void_p(-1) = HWND_TOPMOST; truyền -1 trần thì ctypes cắt còn 32 bit và Windows bỏ qua
        ctypes.windll.user32.SetWindowPos(ctypes.c_void_p(int(self.root.wm_frame(), 16)), ctypes.c_void_p(-1),
                                          0, 0, 0, 0, 0x13)
        self.root.after(2000, self._stay_on_top)

    # ---- nói ----
    def say(self, line, emote, answer=False):
        """answer=True: câu trả lời / lời giải thích cho câu người dùng hỏi, lúc đang hiện thì bấm đơn không tạm dừng."""
        if self.peek:  # đang núp mà có chuyện để nói: ra chỗ cũ, kẻo bong bóng khuất nửa ngoài màn hình
            self.root.geometry("+{}+{}".format(*self.peek["home"]))
            self.peek = None
        self.stop_walk()  # đang đi dạo mà có chuyện để nói thì đứng lại nói
        self.last_said = time.time()
        self.dance_until = 0.0  # đang nhún theo nhạc mà có chuyện để nói: thôi nhún, nói đã
        self.explaining = answer
        self.cur["emote"] = emote = self._face_for(emote)
        self._look()  # emote mới có thể nghiêng phía khác: tính lại hướng lật ngay, khỏi chớp sai 1 khung
        if self.hop:  # đang chuyển động dở mà có câu mới thì làm lại từ đầu
            self.root.after_cancel(self.hop)
        self._animate(motion(emote))
        self.show_bubble(line)
        if emote == "soc":
            self.burst("bang", 2)
        elif emote == "gian_doi":  # dỗi: dấu giận 💢 bốc lên hai bên đầu
            self.burst("anger", 4)

    def start_thinking(self, key, emote=THINK_EMOTE):
        """Gửi câu hỏi xong: dáng dang_nghi (hoặc emote) + câu chờ, ba chấm chạy cho tới khi có câu trả lời (answered)."""
        self.waiting += 1
        self.think_line = pick(key).rstrip(".~ ")
        self.say(self.think_line + "...", emote)
        if self.waiting == 1:
            self.root.after(400, self._think_dots)

    def chew(self, i=0):
        """Được cho "ăn" file: ực một cái bẹp mạnh, rồi nhai nhóp nhép (bẹp nhẹ mỗi 0.28s) tới khi nếm xong (answered)."""
        if i and not self.waiting:
            return
        self._jelly(0.1 if i else 0.3)
        self.root.after(280 if i else 350, self.chew, i + 1)

    def answered(self):
        self.waiting = max(0, self.waiting - 1)

    def _think_dots(self, n=0):
        """Đang chờ trả lời: ba chấm . .. ... cuối câu chờ và chấm tròn hiện dồn 1, 2, 3 rồi tắt hết cạnh đầu
        (mép phải, ngang mắt), cùng nhịp 0.4s."""
        if not self.waiting:
            if self.head_dots:
                self.head_dots.winfo_toplevel().destroy()
                self.head_dots = None
            return
        root, b = self.root, self.bubble
        self.head_dots = self.head_dots or overlay(root)
        win = self.head_dots.winfo_toplevel()
        self.dot_n = n % 4
        self._place_dots()
        if self.state.hidden.is_set():
            win.withdraw()
        else:
            win.update_idletasks()
            win.deiconify()
            win.lift()
        item = next((i for i in b.find_all() if b.type(i) == "text"), None)
        # chỉ đổi đúng câu chờ đã gõ xong (câu khác chen vào, vd báo pin yếu, thì để nguyên)
        if item and self.typing is None and b.itemcget(item, "text").startswith(self.think_line):
            b.itemconfig(item, text=self.think_line + "." * (n % 3 + 1))
        root.after(400, self._think_dots, n + 1)

    def _place_dots(self, x=None, y=None):  # ba chấm bám theo đầu; lúc bị kéo thì đưa toạ độ mới (Tk chưa kịp dời)
        if self.head_dots:
            if x is None:
                x, y = self.root.winfo_x(), self.root.winfo_y()
            # emote đang lật thì dấu "?" sang trái: ba chấm sang trái theo, chấm đầu vẫn sát đầu
            left = self.cur["mouse_flip"] != self.cur["turn"]
            img = (self.dots_left if left else self.dots)[self.dot_n]
            if self.head_dots.cget("image") != str(img):
                self.head_dots.config(image=img)
            self.head_dots.winfo_toplevel().geometry(f"+{x + W // 2 + (-162 if left else 102)}+{y + H - SIZE + 78}")

    # ---- bong bóng ----
    def _type_out(self, item, line, n=1):
        """Chữ hiện dần từng ký tự như đang gõ, ~35 ký tự/giây."""
        self.bubble.itemconfig(item, text=line[:n])
        if n < len(line):
            self.typing = self.root.after(28, self._type_out, item, line, n + 1)
        else:  # gõ xong thật mới bắt đầu đếm giờ đọc (ước lượng theo số chữ thì Tk gõ chậm hơn, đếm hụt)
            self.typing = None
            if self.on_typed:
                self.on_typed()

    def _draw_bubble(self, line):
        """Bong bóng bo góc, viền hồng theo màu tóc, bóng đổ nhạt, đuôi nhọn chỉ xuống nhân vật."""
        c, pad, r, tail = self.bubble, 14, 16, 12
        if self.typing:
            self.root.after_cancel(self.typing)
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
        self._type_out(text, line)

    def _pages_of(self, line, max_h):
        """Chia câu dài thành các trang vừa chỗ trống phía trên đầu (đo bằng chữ thật trên bong bóng): câu dài hơn
        ~5 dòng mà hiện một lần thì phần đầu bị đẩy ra ngoài cửa sổ, mất chữ."""
        b = self.bubble
        probe = b.create_text(0, 0, anchor="nw", width=W - 38, font=("Segoe UI", 11), text="")
        pages, page = [], ""
        for word in line.split():
            test = f"{page} {word}".strip()
            b.itemconfig(probe, text=test + " ▼")
            if page and b.bbox(probe)[3] > max_h:
                pages.append(page)
                page = word
            else:
                page = test
        b.delete(probe)
        return pages + [page]

    def show_bubble(self, line, y=None):
        if y is None:  # ô hỏi đang mở thì mọi câu (tạm dừng, nhột, nhắc việc...) nổi lên trên ô, không che chỗ gõ
            y = ABOVE_ENTRY if self.asking else REST_Y
        room = y - 50 - (0 if y == ABOVE_ENTRY else JUMP)  # 50 = lề trên/dưới + đuôi + bóng đổ của bong bóng
        self._show_page(self._pages_of(line, room), 0, y)

    def _show_page(self, pages, i, y):
        """Hiện lần lượt từng trang như hộp thoại game: trang chưa hết có ▼, bấm vào bong bóng thì sang trang sau
        ngay, không bấm thì gõ xong 5 giây tự sang."""
        last = i == len(pages) - 1
        if self.hide_job:
            self.root.after_cancel(self.hide_job)
            self.hide_job = None
        self.paging = None if last else (pages, i + 1, y)

        def after_typed():  # trang cuối: đọc BUBBLE_SECONDS giây rồi ẩn; trang có ▼: 5 giây rồi tự sang
            job = self._done_talking if last else (lambda: self._show_page(pages, i + 1, y))
            self.hide_job = self.root.after((BUBBLE_SECONDS if last else 5) * 1000, job)

        self.on_typed = after_typed
        self._draw_bubble(pages[i] + ("" if last else " ▼"))
        self.bubble_y = y
        self.bubble.place(relx=0.5, y=y, anchor="s")
        self.bubble.config(cursor="" if last else "hand2")

    def _next_page(self, _):
        if self.paging:
            self._show_page(*self.paging)

    def _done_talking(self):
        """Nói xong (bong bóng ẩn): về dáng bình thường mim_cuoi. Trạng thái kéo dài thì giữ nguyên:
        đang ngủ (buon_ngu), đang tạm dừng (xau_ho che mắt), đang bị kéo (bi_keo). Đang chờ trả lời thì giữ cả bong bóng."""
        if self.waiting:
            return
        self.bubble.place_forget()
        self.explaining = False
        if self.hop and self.cur["emote"] in LOOP_WHILE_TALKING:  # đang nhảy múa dở: dừng luôn, đứng thẳng lại
            self.root.after_cancel(self.hop)
            self.hop = None
            self.cur["turn"] = False
            self.face.place_configure(x=0, y=0)
        s = self.state
        if not (s.sleeping.is_set() or s.paused.is_set() or "prev" in self.drag) and self.cur["emote"] != "mim_cuoi":
            self.pose("mim_cuoi")

    # ---- chuyển động, ký hiệu bay ----
    def _animate(self, path, t0=None):
        """Chạy đường chuyển động: khung chọn theo đồng hồ thật (60 khung/giây), máy bận thì bỏ bớt khung chứ không chậm
        lại, nên nhịp cổ vũ / nhảy theo nhạc luôn đều."""
        now = time.perf_counter()
        t0 = now if t0 is None else t0
        i = min(len(path) - 1, int((now - t0) * 60))
        dx, dy, turn = path[i]
        self.cur["turn"] = bool(turn)
        self.face.place_configure(x=dx, y=-round(dy))
        if self.bubble.winfo_ismapped() and self.bubble_y == REST_Y:  # bong bóng nảy theo đầu, khỏi đè tóc
            self.bubble.place_configure(y=REST_Y - round(max(dy, 0)))
        self._render()
        if i + 1 < len(path):
            self.hop = self.root.after(16, self._animate, path, t0)
        elif self.cur["emote"] in LOOP_WHILE_TALKING and self.talking and "prev" not in self.drag:
            self.hop = self.root.after(16, self._animate, path, now)  # cổ vũ: nhảy tiếp tới khi nói xong câu
        else:
            self.hop = None

    def _puff(self, kind, x, y, step=0, lab=None):
        """Một ký hiệu bay lên ~50px, lắc lư nhẹ, nhỏ dần rồi biến mất (~1.3 giây)."""
        root = self.root
        lab = lab or overlay(root)
        win, t = lab.winfo_toplevel(), step / 40
        if t >= 1 or self.state.hidden.is_set():
            return win.destroy()
        frames = self.glyphs[kind]
        img = frames[int(t * len(frames))]
        lab.config(image=img)
        cx, cy = root.winfo_rootx() + x + 6 * math.sin(t * 7), root.winfo_rooty() + y - 50 * t
        win.geometry(f"+{round(cx - img.width() / 2)}+{round(cy - img.height() / 2)}")
        if step == 0:  # vẽ xong ảnh ở đúng chỗ rồi mới cho hiện, khỏi lóe khung trống
            win.update_idletasks()
            win.deiconify()
        win.lift()  # nổi trên nhân vật kể cả khi nhân vật vừa tự giành lại "trên cùng"
        root.after(33, self._puff, kind, x, y, step + 1, lab)

    def burst(self, kind, n):
        """n ký hiệu bay ra quanh đầu nhân vật, cách nhau 0.15s: Z bên phải đầu, ! 💢 hai bên, ♥ ✦ ngẫu nhiên hai bên."""
        y = H - SIZE + {"z": 60, "heart": 90, "bang": 40, "sparkle": 70, "anger": 30}[kind]
        gap = 350 if kind == "anger" else 150  # giận: từng cái bốc lên chậm rãi, phừng phừng
        for i in range(n):
            side = 1 if kind == "z" else (-1) ** i if kind in ("bang", "anger") else random.choice((-1, 1))
            self.root.after(gap * i, self._puff, kind, W // 2 + side * random.randint(60, 95), y + random.randint(-10, 10))

    def snore(self):
        """Đang ngủ: cứ 1.6 giây một chữ Z bay lên cạnh đầu (chỉ một vòng, kẻo ngủ-dậy-ngủ nhanh thì Z bay gấp đôi)."""
        if self.zz is None:
            self._zzz()

    def _zzz(self):
        if self.state.sleeping.is_set():
            if not self.state.hidden.is_set():
                self.burst("z", 1)
            self.zz = self.root.after(1600, self._zzz)
        else:
            self.zz = None

    # ---- đi dạo ----
    def _stroll(self, dx, steps, i=0):
        """Nhảy lò cò ngang: mỗi bước 16 khung (~0.26s) bật lên 8px, cửa sổ trượt đều theo; xong thì ngồi yên chỗ mới."""
        if i >= steps * 16:
            return self.stop_walk()
        self.root.geometry(f"+{round(self.walk['x0'] + dx * (i + 1) / (steps * 16))}+{self.root.winfo_y()}")
        self.face.place_configure(y=-round(8 * math.sin(math.pi * (i % 16) / 16)))
        self.walk["job"] = self.root.after(16, self._stroll, dx, steps, i + 1)

    def stop_walk(self):  # đi tới nơi, hoặc bị ngắt giữa chừng (có câu mới, bị kéo, bị ẩn, tắt đi dạo)
        if self.walk["job"]:
            self.root.after_cancel(self.walk["job"])
        self.walk.update(dir=None, job=None)
        self.peek_depth, self.peek_img = 0, None
        self.face.place_configure(y=0)

    def start_walk(self):
        """Đi 120-320px sang trái hoặc phải, không ra khỏi màn hình; chỉ đi ngang nên đang ngồi trên taskbar thì vẫn ở đó.
        Không lưu vị trí mới: mở lại chương trình thì về chỗ bạn đã kéo."""
        x, lo, hi = self.root.winfo_x(), self.work[0], self.work[2] - W
        rect = self.perch and window_rect(self.perch["hwnd"])
        if rect:  # đang đứng trên cửa sổ: chỉ đi trong bề ngang cửa sổ đó, chân không thò ra ngoài mép
            lo, hi = rect[0] + 40 - W // 2, rect[2] - 40 - W // 2
        d = random.choice((-1, 1)) * random.randint(120, 320)
        d = max(lo, min(hi, x + (d if lo <= x + d <= hi else -d))) - x  # đụng mép thì quay đầu đi hướng kia
        if abs(d) >= 40:
            self.walk.update(dir="right" if d > 0 else "left", x0=x)
            self.pose(random.choice(["mim_cuoi", "le_luoi", "lap_lanh"]))
            self._stroll(d, max(3, abs(d) // 40))

    @property
    def airborne(self):
        return self.air_job is not None

    def _perch_spots(self):
        """Cửa sổ đứng được: mép trên đủ thấp cho cả đầu lẫn phần lớn bong bóng, đủ rộng, và chỗ giữa mép trên không bị
        cửa sổ khác đè lên. Trên cùng trước."""
        ws, spots = windows(), []
        for i, (h, (l, t, r, b)) in enumerate(ws):
            mx, my = (l + r) // 2, t + 5
            covered = any(L <= mx < R and T <= my < B for _, (L, T, R, B) in ws[:i])
            if not covered and r - l >= 300 and t - H >= self.work[1] - 80 and t < self.work[3] - 60:
                spots.append((h, (l, t, r, b)))
        return spots

    def _perch_under(self, x, feet0, feet1):
        """Cửa sổ có mép trên nằm giữa feet0 và feet1 ngay dưới chân (tâm nhân vật trong bề ngang cửa sổ), trên cùng trước."""
        cx = x + W // 2
        for h, (l, t, r, b) in self._perch_spots():
            if l + 30 <= cx <= r - 30 and feet0 <= t <= feet1:
                return h, t
        return None

    def hop_to_window(self):
        """Nhảy vòng cung lên đứng trên mép trên một cửa sổ đang mở. Không có cửa sổ nào đứng được thì False."""
        spots = self._perch_spots()[:3]
        if not spots:
            return False
        h, (l, t, r, b) = random.choice(spots)
        to_x = random.randint(l + 60, r - 60) - W // 2
        self.walk["dir"] = "right" if to_x > self.root.winfo_x() else "left"
        self.pose(random.choice(["lap_lanh", "mim_cuoi"]))
        self._jump(to_x, t - H, lambda: self._settle(h))
        return True

    def pounce(self, to_x, to_y):
        """Nhảy chồm vòng cung tới (to_x, to_y) (mini game: vồ đồ ăn), chạm đất thì nhún."""
        self.perch = None
        self._jump(to_x, to_y, lambda: self._bump("land"))

    def hop_down(self):
        """Đang đứng trên cửa sổ: nhảy xuống đứng trên taskbar."""
        self.perch = None
        self._jump(self.root.winfo_x(), self.work[3] - H, lambda: (self._bump("land"), self.stop_walk()))

    def _jump(self, to_x, to_y, then, t0=None, x0=None, y0=None):
        """Nhảy vòng cung ~0.65 giây tới (to_x, to_y), đỉnh cao hơn chỗ cao nhất ~90px."""
        if t0 is None:
            t0, x0, y0 = time.perf_counter(), self.root.winfo_x(), self.root.winfo_y()
        k = min(1.0, (time.perf_counter() - t0) / 0.65)
        arc = 90 + max(0, y0 - to_y) * 0.3
        y = y0 + (to_y - y0) * k - arc * 4 * k * (1 - k)
        self.root.geometry(f"+{round(x0 + (to_x - x0) * k)}+{round(y)}")
        if k < 1:
            self.air_job = self.root.after(16, self._jump, to_x, to_y, then, t0, x0, y0)
        else:
            self.air_job = None
            then()

    def _settle(self, hwnd):
        rect = window_rect(hwnd)
        if not rect:  # cửa sổ đóng đúng lúc đang nhảy tới
            return self._fall()
        self.perch = {"hwnd": hwnd, "dx": self.root.winfo_x() - rect[0]}
        self.walk["dir"] = None
        self._bump("land")
        self._perch_watch()

    def _perch_watch(self):
        """Đứng trên cửa sổ: cửa sổ bị kéo đi thì đi theo; đóng / thu nhỏ / phóng to / kéo sát mép trên / thu hẹp tới mức
        chân hụt ra ngoài thì rơi xuống."""
        p = self.perch
        if not p or "prev" in self.drag or self.airborne:
            return
        rect = window_rect(p["hwnd"])
        cx = self.root.winfo_x() + W // 2
        if not rect or rect[1] - SIZE < self.work[1] or not rect[0] + 10 <= cx <= rect[2] - 10:
            self.perch = None
            return self._fall()
        if self.walk["job"]:  # đang đi dạo trên mép cửa sổ: x do đi dạo lo, chỉ bám độ cao
            p["dx"] = self.root.winfo_x() - rect[0]
            x = self.root.winfo_x()
        else:
            x = rect[0] + p["dx"]
        if (x, rect[1] - H) != (self.root.winfo_x(), self.root.winfo_y()):
            self.root.geometry(f"+{x}+{rect[1] - H}")
        self.root.after(30, self._perch_watch)

    def _fall(self, vy=0.0, t=None):
        """Rơi tự do tới khi chạm mép trên một cửa sổ khác bên dưới (đứng luôn lên đó) hoặc chạm taskbar."""
        now = time.perf_counter()
        if t is None:
            self.stop_walk()
            self.pose("soc")
            t = now
        dt = min(0.05, now - t)
        vy += 2600 * dt
        x, y0 = self.root.winfo_x(), self.root.winfo_y()
        y = y0 + vy * dt
        under, floor = self._perch_under(x, y0 + H, y + H), self.work[3] - H
        if under or y >= floor:
            y = under[1] - H if under else floor
            self.root.geometry(f"+{x}+{round(y)}")
            self.air_job = None
            if under:
                self.perch = {"hwnd": under[0], "dx": x - window_rect(under[0])[0]}
                self._perch_watch()
            return self._bump("land", lambda: self.say(pick("fell"), "soc"))
        self.root.geometry(f"+{x}+{round(y)}")
        self.air_job = self.root.after(16, self._fall, vy, now)

    def toggle_walk(self):  # tắt chỉ tới khi thoát chương trình; muốn tắt hẳn thì sửa WALK = False trong config
        self.walk["on"] = not self.walk["on"]
        if not self.walk["on"]:
            self.stop_walk()

    def _slide(self, to, secs, then=None, to_y=None, t0=None, x0=None, y0=None):
        """Trượt tới x = to (và y = to_y nếu có) trong secs giây (chậm - nhanh - chậm), không nhảy; xong thì then()."""
        if t0 is None:
            t0, x0, y0 = time.perf_counter(), self.root.winfo_x(), self.root.winfo_y()
        to_y = y0 if to_y is None else to_y
        k = min(1.0, (time.perf_counter() - t0) / secs)
        e = (1 - math.cos(math.pi * k)) / 2
        self.root.geometry(f"+{round(x0 + (to - x0) * e)}+{round(y0 + (to_y - y0) * e)}")
        if k < 1:
            self.walk["job"] = self.root.after(16, self._slide, to, secs, then, to_y, t0, x0, y0)
        else:
            self.walk["job"] = None
            if then:
                then()

    def _sink(self, depth, secs, then=None, t0=None, d0=None):
        """Thụt hình xuống depth px trong cửa sổ: phần lọt qua đáy cửa sổ (= mép trên taskbar) bị cắt, như núp sau đó."""
        if t0 is None:
            t0, d0 = time.perf_counter(), self.peek_depth
        k = min(1.0, (time.perf_counter() - t0) / secs)
        self.peek_depth = round(d0 + (depth - d0) * (1 - math.cos(math.pi * k)) / 2)
        self.face.place_configure(y=self.peek_depth)
        if k < 1:
            self.walk["job"] = self.root.after(16, self._sink, depth, secs, then, t0, d0)
        else:
            self.walk["job"] = None
            if then:
                then()

    def start_peek(self):
        """Núp ở rìa màn hình, ngẫu nhiên một trong ba kiểu: thụt xuống sau taskbar ở góc dưới chỉ ló đầu lên, nằm ngang
        thò đầu vào từ mép trái / phải, hoặc treo ngược ở mép trên chúc đầu xuống. Chuột lại gần thì nhảy ra, núp chán
        (40-90 giây) thì tự ra. Không lưu vị trí: ra là về đúng chỗ cũ."""
        x, y = self.root.winfo_x(), self.root.winfo_y()
        right = x + W // 2 > (self.work[0] + self.work[2]) / 2
        side = (W - SIZE) // 2  # khoảng trống hai bên hình trong cửa sổ
        hidden = self.work[2] - side if right else self.work[0] - side - SIZE  # x cửa sổ khi hình khuất hẳn ngoài mép
        self.peek = {"home": (x, y), "until": time.time() + random.randint(40, 90), "right": right, "hidden": hidden,
                     "mode": random.choice(("sink", "side", "top"))}
        self.walk["dir"] = "left" if right else "right"  # quay mặt vào trong màn hình
        emote = random.choice(["mim_cuoi", "lap_lanh", "suy_tu"])  # dáng có hướng nhìn: lật được cho mặt hướng vào
        self.pose(emote)
        if self.peek["mode"] == "sink":
            show = round(SIZE * PEEK_SHOW)  # phần bề ngang còn lộ
            to = self.work[2] - show - side if right else self.work[0] + show - side - SIZE
            return self._slide(to, 0.9, lambda: self._sink(SIZE - PEEK_HEAD, 0.6, self._peek_watch), to_y=self.work[3] - H)
        # chạy khuất hẳn ra ngoài mép, đổi sang ảnh xoay, hiện ra ở chỗ núp (ngoài màn hình) rồi thò đầu vào
        if self.peek["mode"] == "side":  # nằm ngang ở mép trái / phải, độ cao ngẫu nhiên
            top, bottom = self.work[1] - (H - SIZE) + 40, self.work[3] - H
            y0 = random.randint(min(top, bottom), bottom)
            start, end, angle = (hidden, y0), (self.work[2] - SIDE_HEAD - side if right else
                                               self.work[0] + SIDE_HEAD - side - SIZE, y0), 90 if right else -90
        else:  # treo ngược ở mép trên, vị trí ngang ngẫu nhiên
            x0 = random.randint(self.work[0] - side, self.work[2] - W + side)
            start, end, angle = (x0, self.work[1] - H), (x0, self.work[1] + SIDE_HEAD - H), 180
        self.peek["retract"] = start  # bị phát hiện / chán: rụt về đây (khuất ngoài mép) rồi mới ra

        def poke_in():
            self.peek_img = peek_frame(emote, angle)
            self.root.geometry("+{}+{}".format(*start))
            self.root.update_idletasks()  # Tk dời cửa sổ ngay, kẻo _slide đọc vị trí cũ rồi kéo về chỗ cũ
            self._render()
            self._slide(end[0], 0.7, self._peek_watch, to_y=end[1])

        self._slide(hidden, 0.7, poke_in)

    def _peek_watch(self):
        if not self.peek:
            return
        px, py = self.root.winfo_pointerxy()
        # phần hình đang lộ trên màn hình; chuột vào gần trong 150px là bị phát hiện
        left = max(self.root.winfo_rootx() + (W - SIZE) // 2, self.work[0])
        right = min(self.root.winfo_rootx() + (W + SIZE) // 2, self.work[2])
        top, bottom = self.root.winfo_rooty() + H - SIZE + self.peek_depth, self.root.winfo_rooty() + H
        found = left - 150 < px < right + 150 and top - 150 < py < bottom + 150
        if found or time.time() > self.peek["until"]:  # bị phát hiện: ra nhanh rồi nói; núp chán: ra chậm, lặng lẽ
            self._leave_peek(found)
        else:
            self.root.after(100, self._peek_watch)

    def _leave_peek(self, found):
        p, self.peek = self.peek, None
        (hx, hy), fast = p["home"], 0.4 if found else 1.0
        done = (lambda: self.say(pick("peek_found"), "le_luoi")) if found else self.stop_walk
        if p["mode"] == "sink":  # trồi lên rồi về chỗ cũ
            return self._sink(0, fast / 2, lambda: self._slide(hx, fast, done, to_y=hy))

        def come_out():  # đã rụt đầu ra ngoài mép: đứng thẳng lại ở mép trái / phải ngang chỗ cũ, rồi chạy vào
            self.peek_img = None
            self.root.geometry(f"+{p['hidden']}+{hy}")
            self.root.update_idletasks()
            self._render()
            self._slide(hx, fast + 0.3, done, to_y=hy)

        rx, ry = p["retract"]
        self._slide(rx, fast / 2, come_out, to_y=ry)

    def pointer_on_me(self):  # chuột đang ở trên nhân vật: có thể sắp bấm, đừng chạy mất
        px, py = self.root.winfo_pointerxy()
        return 0 <= px - self.root.winfo_rootx() < W and 0 <= py - self.root.winfo_rooty() < H

    def reset_position(self):  # lỡ kéo nhân vật ra khuất màn hình thì gọi về
        POS_FILE.unlink(missing_ok=True)
        self.root.geometry(f"+{self.work[2] - W}+{self.work[3] - H}")

    # ---- chuột: kéo thả, bấm, xoa đầu ----
    def _press(self, e):
        self.peek = self.perch = None  # đang trốn ở rìa / đứng trên cửa sổ mà bị tóm: thôi, kéo đi từ chỗ đó
        if self.air_job:  # tóm được giữa lúc đang nhảy / rơi
            self.root.after_cancel(self.air_job)
            self.air_job = None
        self.stop_walk()  # bị nhấc lên kéo thì thôi đi dạo
        if self.drag.get("fly"):  # bắt được giữa lúc đang bay: kéo tiếp luôn từ chỗ đó
            self.root.after_cancel(self.drag.pop("fly"))
            x, y = map(int, self.drag["pos"].split())
            return self.drag.update(x=e.x_root, y=e.y_root, wx=x, wy=y, moved=True, trail=[])
        self.drag.update(x=e.x_root, y=e.y_root, wx=self.root.winfo_x(), wy=self.root.winfo_y(), moved=False)

    def _move(self, e):
        drag = self.drag
        if "x" not in drag:  # giữ chuột từ chỗ khác rồi rê vào nhân vật: không phải kéo nhân vật
            return
        dx, dy = e.x_root - drag["x"], e.y_root - drag["y"]
        drag["moved"] = drag["moved"] or abs(dx) + abs(dy) > 5  # rung tay vài px vẫn tính là bấm
        if drag["moved"]:
            if "prev" not in drag:  # vừa bị nhấc lên: đổi sang ảnh bị xách cổ áo, nhớ emote cũ để thả ra thì đổi lại
                drag.update(prev=self.cur["emote"], since=time.time())
                self.state.dragging.set()
                if self.hop:
                    self.root.after_cancel(self.hop)
                    self.hop = None
                self.face.place_configure(x=0, y=0)
                self.cur["turn"] = False
                self.swing.update(a=0.0, v=0.0, x=None, vx=0.0, t=None)
                self.pose(DRAG_EMOTE)
                self._swing()
                if not self.waiting:  # đang nghĩ thì giữ nguyên bong bóng "đang nghĩ"
                    self.show_bubble(pick("dont_throw" if time.time() < self.dizzy_until else "dragged"))
            self._put(drag["wx"] + dx, drag["wy"] + dy)
            now = time.perf_counter()  # vết tay kéo ~0.1s gần nhất: thả ra thì tính đà từ đây
            drag["trail"] = [p for p in drag.get("trail", []) if now - p[0] < 0.1] + [(now, drag["wx"] + dx, drag["wy"] + dy)]
            # đường kéo vài giây gần nhất: thả ra mà trước đó bị cầm quay vòng / lắc nhiều thì chóng mặt
            drag["path"] = [p for p in drag.get("path", []) if now - p[0] < SPIN_WINDOW] + [(now, drag["wx"] + dx,
                                                                                                drag["wy"] + dy)]

    def _put(self, x, y):
        """Dời cửa sổ tới (x, y), nhớ lại để lưu vị trí / tính lắc (Tk chưa kịp dời nên không đọc lại winfo_x)."""
        self.drag["pos"], self.drag["cx"] = f"{round(x)} {round(y)}", x
        self.root.geometry(f"+{round(x)}+{round(y)}")
        self._place_dots(round(x), round(y))

    def _swing(self):
        """Bị xách cổ áo như con lắc: kéo nhanh thì người bị bỏ lại phía sau, đổi hướng / dừng tay thì đung đưa
        qua lại vài nhịp rồi đứng yên. Chạy ~60 lần/giây tới khi thả ra."""
        s, d = self.swing, self.drag
        if "prev" not in d:
            return
        now = time.perf_counter()
        # dt tính theo khung 16ms: hẹn giờ của Windows lệch 15-30ms, không bù thì lúc nhanh lúc chậm trông giật
        dt = 1.0 if s["t"] is None else max(0.5, min(3.0, (now - s["t"]) / 0.016))
        x = d.get("cx", d["wx"])
        raw = 0.0 if s["x"] is None else (x - s["x"]) / dt  # px mỗi khung
        vx = s["vx"] + (raw - s["vx"]) * min(1.0, 0.4 * dt)  # lọc: chuột gửi vị trí không đều, khung có khung không
        ax = (vx - s["vx"]) / dt
        s.update(t=now, x=x, vx=vx)
        # lò xo mềm kéo về góc "bị bỏ lại" (đi sang phải thì chân lệch trái = quay chiều kim đồng hồ = góc âm),
        # giảm chấn nhẹ cho đung đưa vài nhịp, tay tăng/giảm tốc thì người bị giật ngược lại
        s["v"] += (0.05 * (-0.4 * vx - s["a"]) - 0.10 * s["v"] - 0.2 * ax) * dt
        s["a"] = max(-40.0, min(40.0, s["a"] + s["v"] * dt))
        self._render()
        self.root.after(16, self._swing)

    def _release(self, e):
        trail, now = self.drag.get("trail", []), time.perf_counter()
        self.drag["spun"] = spun(self.drag.get("path", []))
        if self.drag.get("moved") and len(trail) > 1 and now - trail[-1][0] < 0.06:  # còn đang vung tay lúc thả
            (t0, x0, y0), (t1, x1, y1) = trail[0], trail[-1]
            vx, vy = (x1 - x0) / max(t1 - t0, 0.01), (y1 - y0) / max(t1 - t0, 0.01)  # px/giây
            speed = math.hypot(vx, vy)
            if speed > THROW_SPEED:  # quăng: bay tiếp theo đà, đụng rìa màn hình thì nảy
                k = min(1.0, THROW_MAX / speed)
                self.drag.update(fx=x1, fy=y1, vx=vx * k, vy=vy * k, ft=now)
                return self._fly()
        self._land()

    def _fly(self):
        """Bay theo đà sau khi bị quăng: chậm dần, đụng rìa vùng làm việc (phần có hình nhân vật, không tính khoảng
        trống trong cửa sổ) thì nảy ngược lại mất bớt lực, dấu "!" bật ra chỗ va; chậm hẳn thì đáp xuống."""
        d, now = self.drag, time.perf_counter()
        dt, d["ft"] = min(0.05, now - d["ft"]), now
        d["fx"] += d["vx"] * dt
        d["fy"] += d["vy"] * dt
        decay = math.exp(-THROW_FRICTION * dt)
        d["vx"] *= decay
        d["vy"] *= decay
        side = (W - SIZE) // 2  # khoảng trống hai bên hình trong cửa sổ
        box = {"x": (self.work[0] - side, self.work[2] - W + side), "y": (self.work[1] - (H - SIZE), self.work[3] - H)}
        for axis, (lo, hi) in box.items():
            p, v = "f" + axis, "v" + axis
            if not lo <= d[p] <= hi:
                d[p] = max(lo, min(hi, d[p]))
                if abs(d[v]) > 150:  # va đủ mạnh mới bật "!", lăn nhẹ vào rìa thì thôi
                    spot = {("x", lo): (side, H - SIZE // 2), ("x", hi): (W - side, H - SIZE // 2),
                            ("y", lo): (W // 2, H - SIZE + 10), ("y", hi): (W // 2, H - 20)}[axis, lo if d[p] == lo else hi]
                    self._puff("bang", *spot)
                    self._bump("side" if axis == "x" else "land")
                    d["hits"] = d.get("hits", 0) + 1
                d[v] *= -THROW_BOUNCE
        self._put(d["fx"], d["fy"])
        if math.hypot(d["vx"], d["vy"]) < 90:  # chậm hẳn: đáp
            d.pop("fly", None)
            return self._land()
        d["fly"] = self.root.after(16, self._fly)

    def _land(self):
        held = dict(self.drag)
        self.drag.clear()  # mỗi lần nhấn chỉ dùng một lần
        self.state.dragging.clear()
        # nhả chuột mà trước đó không nhấn trên nhân vật (nhân vật đi dạo trượt tới dưới con trỏ),
        # hoặc nhả của cú bấm đúp (lần nhấn thứ 2 chỉ gọi open_ask, không qua press): bỏ qua
        if "moved" not in held:
            return
        if held["moved"]:
            # lưu toạ độ vừa tính, không đọc winfo_x(): Tk chưa kịp dời cửa sổ nên nó còn trả chỗ cũ
            POS_FILE.write_text(held["pos"])
            x, y = map(int, held["pos"].split())
            under = self._perch_under(x, y + H - 40, y + H + 40)  # thả ngay trên mép trên cửa sổ: đứng luôn lên đó
            if under:
                self.root.geometry(f"+{x}+{under[1] - H}")
                self.perch = {"hwnd": under[0], "dx": x - window_rect(under[0])[0]}
                self.root.after(30, self._perch_watch)
            if self.last_said > held["since"]:  # có câu mới (vd câu trả lời) lúc đang bị kéo: giữ câu đó, đừng đè
                return
            if self.waiting:  # đang nghĩ: về dáng đang nghĩ, giữ bong bóng chờ
                self.pose(held["prev"])
                return self._bump("land")
            if held.get("hits", 0) >= 2 or held.get("spun"):  # bị quăng nảy mấy lần / cầm quay vòng: đáp xuống chóng mặt
                self.pose(DIZZY_EMOTE)
                return self._bump("land", self._get_dizzy)
            # đáp xuống, bẹp một cái rồi nói: chỉ giữ dáng của trạng thái kéo dài (tạm dừng che mắt, buồn ngủ); còn lại về
            # dáng thường, kẻo đang cổ vũ mà bị kéo thì thả ra lại cầm lightstick nhảy thêm cả chục giây
            prev = held["prev"]
            emote = prev if prev in ("xau_ho", "buon_ngu") else random.choice(("mim_cuoi", "le_luoi"))
            self.pose(emote)
            self._bump("land", lambda: self.say(pick("dropped"), emote))
        else:
            # chờ hết thời gian bấm đúp của Windows (mặc định 500ms) rồi mới tính là bấm đơn, kẻo bấm đúp chậm bị nhầm
            self.click_job = self.root.after(ctypes.windll.user32.GetDoubleClickTime(), self._clicked)

    def _bump(self, kind, then=None, i=0):
        """Nhún: vài khung bẹp / giãn rồi về dáng thường (đáy giữ nguyên chỗ), xong thì làm then()."""
        if i == 0 and self.bump_job:
            self.root.after_cancel(self.bump_job)
        steps = BUMPS[kind]
        if i == len(steps):
            self.squash_img = self.bump_job = None
            self._render()
            return then() if then else None
        c = self.cur
        self.squash_img = squash_frame(c["emote"], c["mouse_flip"] != c["turn"], *steps[i])
        self._render()
        self.bump_job = self.root.after(40, self._bump, kind, then, i + 1)

    @property
    def dancing(self):
        return time.time() < self.dance_until

    def dance(self, seconds=8, bpm=110):
        """Nhún theo nhạc: lắc lư qua lại mỗi 2 nhịp, nhún xuống mỗi nhịp (Windows không cho biết nhịp bài, ~110 nhịp/phút
        hợp đa số nhạc pop), nốt nhạc ♪ ♫ bay lên quanh đầu. Có câu mới để nói / bị nhấc lên thì thôi."""
        beat = 60 / bpm * 60  # số khung (60 khung/giây) mỗi nhịp
        path = [(round(7 * math.sin(math.pi * i / beat)), 6 * abs(math.sin(math.pi * i / beat)), 0)
                for i in range(int(seconds * 60))] + [(0, 0, 0)]
        if self.hop:
            self.root.after_cancel(self.hop)
        self.pose(random.choice(["lap_lanh", "mim_cuoi", "le_luoi"]))
        self.dance_until = time.time() + seconds
        self._animate(path)
        for k in range(int(seconds / 0.6)):
            self.root.after(int(k * 600 + random.randint(0, 200)), self._note)

    def _note(self):
        if self.dancing and "prev" not in self.drag and not self.state.hidden.is_set():
            side = random.choice((-1, 1))
            self._puff(random.choice(("note", "notes")), W // 2 + side * random.randint(55, 100),
                       H - SIZE + random.randint(40, 100))

    def _get_dizzy(self):
        """Đáp xuống sau cú quăng mạnh: mắt xoáy (ảnh có sẵn sao quanh đầu), kêu chóng mặt, lảo đảo; 60 giây tới nhấc lên
        thì kêu đừng quăng."""
        self.dizzy_until = time.time() + 60
        self.say(pick("dizzy"), DIZZY_EMOTE)
        if self.hop:
            self.root.after_cancel(self.hop)
        self._animate(DIZZY_PATH)

    def _clicked(self):
        self.click_job = None
        if self.answering:
            return self._next_page(None)  # đang nghĩ / đang giải thích: bấm không che mắt, câu dài thì sang trang
        if self.asking:  # đang mở ô hỏi: bấm không che mắt, chỉ đưa con trỏ về ô để gõ tiếp
            self.root.focus_force()
            return self.entry.focus_set()
        self.on_click()

    def _stroke(self, e):
        """Xoa đầu: rê chuột qua lại thật sự trên nửa trên nhân vật (xem rubbed) thì bàn tay hiện ra xoa kiểu petpet;
        rê chuột tí / lướt ngang qua đầu thì không. Đã xoa rồi thì _pet tự theo chuột, xoa đến khi thôi."""
        pat, now = self.pat, time.time()
        if e.y > self.face.winfo_height() * 0.45:
            pat["xs"] = []
            return
        pat["xs"] = [p for p in pat["xs"] if now - p[0] <= RUB_WINDOW] + [(now, e.x)]
        if self.pet_job or "prev" in self.drag or not rubbed(pat["xs"]):
            return
        pat["xs"], pat["last"] = [], now
        if self.cur["emote"] != PUFF_EMOTE and not self.waiting:
            self.pose(PUFF_EMOTE)  # bị xoa đầu là phê ngay
        self._pet()

    def _pet(self, i=0):
        """Bàn tay xoa đầu chạy theo video petpet, 30 khung/giây: nắm ấn đầu bẹp dí, nhấc lên, xoè ra, lặp lại (~4 lần
        mỗi giây). Xoa mãi được: còn rê chuột trên người là còn xoa; chuột rời ra hoặc đứng yên 1.2 giây thì rút tay,
        đầu nhún nhảy rồi về dáng cũ. Đọc vị trí chuột trực tiếp vì lúc đầu bẹp, chỗ chuột thành nền trong suốt
        (chuột lọt xuống cửa sổ bên dưới) nên không còn sự kiện rê chuột."""
        if self.bump_job:  # đang xoa thì tay giữ quyền bẹp / giãn
            self.root.after_cancel(self.bump_job)
            self.bump_job = None
        pat, now = self.pat, time.time()
        px, py = self.root.winfo_pointerxy()
        left, top = self.root.winfo_rootx() + (W - SIZE) // 2, self.root.winfo_rooty() + H - SIZE
        # cả người + chỗ tay che: đang xoa chuột hay trôi xuống mặt / ra mép, đừng vì thế mà tắt
        on_me = left - 40 <= px <= left + SIZE + 40 and top - 130 <= py <= top + SIZE
        if on_me and (px, py) != pat["xy"]:
            pat["last"] = now
        pat["xy"] = (px, py)
        if now - pat["last"] > 1.2 or "prev" in self.drag:  # rời chuột ra / để chuột yên 1.2s: thôi xoa
            self.pet_job = None
            self._hand_at(None)
            self.root.after(2600, self._pet_end)
            return self._jelly(0.4)
        pose = PET_SEQ[i % len(PET_SEQ)]
        s, c = PET_SQUASH[pose], self.cur
        self.squash_img = squash_frame(c["emote"], c["mouse_flip"] != c["turn"], round(1 + 0.6 * s, 2), round(1 - s, 2))
        self._render()
        self._bubble_above(round(SIZE * max(0.0, -s)))
        self._hand_at(pose, s)
        self.pet_job = self.root.after(33, self._pet, i + 1)

    def _pet_end(self):
        """Thôi xoa ~2.5 giây mà không đang nói gì: hết phê, về mặt bình thường."""
        if (time.time() - self.pat["last"] >= 2.5 and self.cur["emote"] == PUFF_EMOTE and not self.talking
                and "prev" not in self.drag):
            self.pose("mim_cuoi")

    def _jelly(self, strength=0.2, t0=None):
        """Bẹp dí rồi nảy như thạch (~1 giây): lò xo tắt dần, bẹp thì thấp + bè ra, bật lên thì cao + thon lại; đáy hình
        đứng yên chỗ cũ. Bẹp / giãn làm tròn từng nấc 0.02 nên mỗi dáng chỉ dựng vài chục ảnh rồi dùng lại."""
        now = time.perf_counter()
        if t0 is None:
            if self.bump_job:
                self.root.after_cancel(self.bump_job)
            t0 = now
        t = now - t0
        s = round(strength * math.exp(-t / 0.35) * math.cos(2 * math.pi * 3.2 * t) / 0.02) * 0.02
        if t > 1.1 or "prev" in self.drag:
            self.squash_img = self.bump_job = None
            self._bubble_above(0)
            return self._render()
        c = self.cur
        self.squash_img = squash_frame(c["emote"], c["mouse_flip"] != c["turn"], round(1 + 0.6 * s, 2),
                                       round(1 - s, 2)) if s else None
        self._render()
        self._bubble_above(round(SIZE * max(0.0, -s)))  # nảy giãn cao hơn: bong bóng dâng theo, khỏi đè tóc
        self.bump_job = self.root.after(16, self._jelly, strength, t0)

    def _hand_at(self, pose, s=0.0):
        """Bàn tay dáng pose (a-d, ảnh trong ban_tay/) úp lên đỉnh đầu đang bẹp s (đỉnh đầu tụt SIZE*s px); None: cất tay."""
        if pose is None:
            if self.hand:
                self.hand.winfo_toplevel().withdraw()
            return
        if self.hand is None:
            self.hand = overlay(self.root)
        self.hand.config(image=self.hand_imgs[pose])
        win = self.hand.winfo_toplevel()
        x = self.root.winfo_rootx() + (W - SIZE) // 2 + PET_HAND_X
        y = self.root.winfo_rooty() + H - SIZE + round(SIZE * s) - PET_HAND_Y[pose]
        win.geometry(f"+{x}+{y}")
        if win.state() != "normal":
            win.update_idletasks()
            win.deiconify()
        win.lift()

    def _bubble_above(self, rise):
        """Hình cao hơn bình thường rise px (giãn / phồng to): đẩy bong bóng lên ngần ấy, kẻo nền bong bóng đè cắt tóc."""
        if self.bubble.winfo_ismapped() and self.bubble_y == REST_Y:
            self.bubble.place_configure(y=REST_Y - rise)

    # ---- ô hỏi, ẩn/hiện ----
    def open_ask(self):
        if self.click_job:  # cú bấm đầu của bấm đúp: không tính là bấm đơn
            self.root.after_cancel(self.click_job)
            self.click_job = None
        if self.answering:  # đang nghĩ / đang giải thích câu trước: chưa cho hỏi tiếp
            return
        if self.state.hidden.is_set():
            self.show_hide()
        self.show_bubble(pick("ask_hint"), y=ABOVE_ENTRY)
        self.entry.delete(0, "end")
        self.entry.place(relx=0.5, y=ENTRY_Y, anchor="s", width=W - 24, height=34)
        self.root.focus_force()  # cửa sổ không viền phải giành focus thì mới gõ được
        self.entry.focus_set()

    def close_ask(self, bubble=False):
        self.entry.place_forget()
        if bubble:
            self.bubble.place_forget()

    def _send_ask(self, _):
        question = self.entry.get().strip()
        self.close_ask(bubble=not question)
        if question:
            self.on_ask(question)

    def show_hide(self):
        hidden = self.state.hidden
        if hidden.is_set():
            hidden.clear()
            self.root.deiconify()
        else:  # ẩn xuống khay: không hiện, không chụp màn hình
            if self.peek:
                self.root.geometry("+{}+{}".format(*self.peek["home"]))
                self.peek = None
            self.stop_walk()
            hidden.set()
            self.close_ask()
            self.root.withdraw()

    def show(self):  # nhắc việc, hỏi từ khay...: hiện lên dù đang ẩn
        if self.state.hidden.is_set():
            self.show_hide()
