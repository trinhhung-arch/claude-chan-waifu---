"""Chế độ tập trung (Pomodoro): đếm giờ, dỗi khi mở trang gây xao nhãng, hết giờ thì khen và nhắc nghỉ.
Focus(char, state, on_change).start(); on_change() gọi khi chữ trên menu khay cần đổi."""
import math
import time

from ..core.config import BREAK_MINUTES, FOCUS_BLOCK, FOCUS_MINUTES, TITLE, tr
from ..desktop import active_title
from ..dialogue import pick


class Focus:
    def __init__(self, char, state, on_change=lambda: None):
        self.char, self.state, self.on_change = char, state, on_change
        self.f = {"until": 0.0, "break_until": 0.0, "nag": 0.0, "left": None, "minutes": FOCUS_MINUTES}

    def start(self):
        self.char.root.after(2000, self.check)

    def begin(self, minutes, announce=True):
        """Bắt đầu (hoặc bắt đầu lại) một phiên tập trung. Từ câu nói với nhân vật thì câu trả lời đã báo rồi, khỏi nói thêm."""
        self.f.update(until=time.time() + minutes * 60, break_until=0.0, left=None, minutes=minutes)
        if announce:
            self.char.say(pick("focus_start", m=minutes), "co_vu")
        self.on_change()

    def toggle(self):
        if self.f["until"]:
            self.f["until"] = 0.0
            self.char.say(pick("focus_stop"), "mim_cuoi")
            self.on_change()
        else:
            self.begin(FOCUS_MINUTES)

    def label(self, _=None):
        if not self.f["until"]:
            return tr("Tập trung {m} phút").format(m=FOCUS_MINUTES)
        return tr("Dừng tập trung (còn {m} phút)").format(m=max(1, math.ceil((self.f["until"] - time.time()) / 60)))

    def check(self):
        """Hết giờ tập trung: khen + nhắc nghỉ. Đang tập trung mà mở trang trong FOCUS_BLOCK: dỗi (mỗi phút tối đa 1 lần).
        Hết giờ nghỉ: gọi quay lại. Đang gõ câu hỏi thì để lượt sau."""
        char, f, now = self.char, self.f, time.time()
        if not char.asking:
            if f["until"] and now >= f["until"]:
                f.update(until=0.0, break_until=now + BREAK_MINUTES * 60)
                char.say(pick("focus_done", m=f["minutes"], b=BREAK_MINUTES), "nhay_mat_ok")
                self.on_change()
            elif f["until"]:
                title = active_title()
                title = self.state.seen_title if title == TITLE else title
                if any(w in title.lower() for w in FOCUS_BLOCK) and now - f["nag"] > 60 and not char.thinking:
                    f["nag"] = now
                    char.say(pick("focus_nag"), "gian_doi")
                left = math.ceil((f["until"] - now) / 60)
                if left != f["left"]:  # menu không tự đổi chữ: dựng lại mỗi phút cho "còn N phút" đúng
                    f["left"] = left
                    self.on_change()
            elif f["break_until"] and now >= f["break_until"]:
                f["break_until"] = 0.0
                char.say(pick("break_done"), "co_vu")
        char.root.after(2000, self.check)
