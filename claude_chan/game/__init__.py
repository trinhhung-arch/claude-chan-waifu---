"""Mini game giành đồ ăn: một món ăn hiện ở chỗ ngẫu nhiên trên màn hình, Claude-chan hoá dáng bò 4 chân lon ton chạy
tới (càng lúc càng nhanh), tới gần thì nhảy chồm vồ;
người chơi túm kéo / quăng cô ấy ra xa. Giữ được GAME_SECONDS giây là thắng; quăng mạnh tới chóng mặt thì cô ấy đứng
im tới khi nói xong câu chóng mặt."""
import math
import random
import time

from ..character import food_image, overlay
from ..core.config import CRAWL_EMOTE, DIZZY_EMOTE, SIZE
from ..dialogue import pick

GAME_SECONDS = 20
POUNCE_RANGE = 230  # cách đồ ăn chừng này px thì thôi bò, nhảy chồm tới vồ
FOODS = "🍰🍩🍓🍙🍡🍪"


def far_spot(work, mouth, rnd=random):
    """Chỗ đặt đồ ăn trong vùng làm việc (trái, trên, phải, dưới), cách mép 60px, cách miệng nhân vật ít nhất 350px
    nếu được (màn hình nhỏ quá thì lấy chỗ xa nhất trong vài lần thử)."""
    l, t, r, b = work
    tries = [(rnd.randint(l + 60, r - 60), rnd.randint(t + 60, b - 60)) for _ in range(30)]
    return max(tries, key=lambda p: min(350, math.dist(p, mouth)))


def step(x, y, tx, ty, d):
    """Đi d px từ (x, y) thẳng về phía (tx, ty), không vượt quá đích."""
    dist = math.dist((x, y), (tx, ty))
    k = 1.0 if dist <= d else d / dist
    return x + (tx - x) * k, y + (ty - y) * k


class FoodGame:
    def __init__(self, char):
        self.char, self.job, self.lab = char, None, None

    def start(self):
        c = self.char
        if self.job or c.answering or c.asking or c.state.hidden.is_set():
            return
        c.peek = c.perch = None
        c.stop_walk()
        self.img = food_image(random.choice(FOODS))
        self.lab = overlay(c.root)
        self.lab.config(image=self.img)
        win = self.lab.winfo_toplevel()
        self.fx, self.fy = far_spot(tuple(c.work), self._mouth(c.root.winfo_x(), c.root.winfo_y()))
        win.geometry(f"+{self.fx - self.img.width() // 2}+{self.fy - self.img.height() // 2}")
        win.update_idletasks()
        win.deiconify()
        c.playing = True
        self.pounced = 0.0  # lần nhảy chồm gần nhất
        self.x = None  # vị trí cửa sổ nhân vật (số thực) do game tự dời; None: đọc lại từ Tk (vừa bị kéo / quăng)
        self.t0 = self.t = time.perf_counter()
        c.say(pick("game_start"), CRAWL_EMOTE)
        self.job = c.root.after(16, self._tick)

    def x0(self):
        return self.char.root.winfo_x()

    def y0(self):
        return self.char.root.winfo_y()

    def _mouth(self, x, y):
        r = self.char.root
        return x + r.winfo_width() / 2, y + r.winfo_height() - SIZE * 0.45

    def _tick(self):
        c, now = self.char, time.perf_counter()
        dt, self.t = min(0.05, now - self.t), now
        if c.state.hidden.is_set():  # ẩn xuống khay giữa chừng: thôi chơi, không nói gì
            return self._end(None)
        if now - self.t0 >= GAME_SECONDS:
            return self._end(True)
        self.lab.winfo_toplevel().lift()
        held = "prev" in c.drag or c.drag.get("fly") or c.airborne
        if held or c.cur["emote"] == DIZZY_EMOTE:  # đang bị túm / quăng / chóng mặt: đứng im
            self.x = None
        else:
            if self.x is None:
                self.x, self.y = c.root.winfo_x(), c.root.winfo_y()
            mx, my = self._mouth(self.x, self.y)
            dist = math.dist((mx, my), (self.fx, self.fy))
            if dist < 40:
                return self._end(False)
            if c.cur["emote"] != CRAWL_EMOTE:  # bị thả xuống / nói câu khác xong: về lại dáng bò chạy tiếp
                c.pose(CRAWL_EMOTE)
            if dist < POUNCE_RANGE and now - self.pounced > 1.2:  # đủ gần: nhảy chồm vồ
                self.pounced, self.x = now, None
                c.walk["dir"] = "right" if self.fx > mx else "left"
                c.face.place_configure(y=0)
                c.pounce(round(self.x0() + self.fx - mx), round(self.y0() + self.fy - my))
                self.job = c.root.after(16, self._tick)
                return
            speed = 180 + 160 * (now - self.t0) / GAME_SECONDS  # px/giây, càng lúc càng hăng
            nx, ny = step(mx, my, self.fx, self.fy, speed * dt)
            self.x, self.y = self.x + nx - mx, self.y + ny - my
            c.perch = None  # thả lên mép cửa sổ thì cũng nhảy xuống chạy tiếp
            c.walk["dir"] = "right" if self.fx > mx else "left"  # mặt nhìn về phía đồ ăn
            c.root.geometry(f"+{round(self.x)}+{round(self.y)}")
            if not c.hop:  # lon ton: bước ngắn nảy nhẹ, nhanh như chân ngắn chạy
                c.face.place_configure(y=-round(5 * abs(math.sin(now * 18))))
        self.job = c.root.after(16, self._tick)

    def _end(self, won):
        """won: True = người chơi giữ được tới hết giờ, False = Claude-chan ăn mất, None = dừng ngang."""
        c = self.char
        self.job, c.playing = None, False
        c.walk["dir"] = None
        c.face.place_configure(y=0)
        self.lab.winfo_toplevel().destroy()
        if won:
            c.say(pick("game_win"), "buon")
        elif won is False:
            c.say(pick("game_lose"), "phan_khich")
            c.burst("sparkle", 4)
