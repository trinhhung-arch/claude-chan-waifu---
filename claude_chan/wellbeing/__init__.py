"""Chăm người dùng: chào mỗi ngày, ngủ gục khi rời máy, nhắc nghỉ khi ngồi lâu / thức khuya, báo pin yếu và mất mạng.
Wellbeing(char, state).start() rồi để nó tự chạy."""
import time
from datetime import date

from ..core.config import AWAY_MINUTES, LOW_BATTERY, NIGHT_HOURS, TIRED_HOURS, YAWN_EMOTE
from ..desktop import battery, fullscreen, idle_seconds, online
from ..dialogue import greeting, name_from, pick, special_day
from ..memory import favorite_food, load_memory


class Wellbeing:
    """char: nhân vật (say, burst, snore, asking, thinking, root). state: trạng thái chung (đặt sleeping)."""

    def __init__(self, char, state):
        self.char, self.state = char, state
        self.rest = {"start": time.time(), "next_tired": TIRED_HOURS * 3600, "night": None, "greeted": None}
        self.power = {"low": False, "online": True}
        self.lunch = None  # ngày đã rủ ăn trưa

    def start(self):
        self.greet()
        after = self.char.root.after
        after(20000, self.check_rest)  # để câu chào hiện đủ rồi mới xét buồn ngủ (mở máy lúc nửa đêm)
        after(20000, self.check_system)

    def greet(self):
        """Chào một lần mỗi ngày: dịp đặc biệt (sinh nhật, Tết, Trung thu, thứ Hai/Sáu) hoặc chào theo giờ."""
        memory, hour, today = load_memory(), time.localtime().tm_hour, date.today()
        special = special_day(today, hour, memory, name_from(memory))
        line, emote = special or greeting(hour, name_from(memory))
        self.rest["greeted"] = today
        if not special and hour in NIGHT_HOURS:  # câu chào đã nhắc khuya rồi, đêm nay khỏi nhắc lại
            self.rest["night"] = today.isoformat()
        self.char.say(line, emote)
        if special:
            self.char.burst("heart", 5)

    def check_rest(self):
        """Rời máy quá AWAY_MINUTES: ngủ gục, ngừng chụp. Quay lại: tỉnh dậy. Ngồi lâu / quá nửa đêm: buồn ngủ, nhắc nghỉ.
        Đang gõ câu hỏi thì không nói gì, kẻo bong bóng che ô nhập."""
        char, rest, sleeping = self.char, self.rest, self.state.sleeping
        idle, now = idle_seconds(), time.time()
        # xem video / chơi game toàn màn hình thì không chạm chuột vẫn là đang dùng máy
        if idle >= AWAY_MINUTES * 60 and not fullscreen():
            if not sleeping.is_set():
                sleeping.set()
                if not char.asking:
                    char.say(pick("away"), "buon_ngu")
                char.snore()
        elif sleeping.is_set():
            sleeping.clear()
            rest.update(start=now - idle, next_tired=TIRED_HOURS * 3600)  # rời máy đủ lâu: đếm giờ ngồi lại từ đầu
            if not char.asking:
                if rest["greeted"] != date.today():  # qua ngày mới (để máy qua đêm): chào ngày mới thay cho "về rồi"
                    self.greet()
                else:
                    char.say(pick("back"), "lap_lanh")
        elif not (char.asking or char.thinking):  # nhắc nghỉ / nhắc khuya để sau khi trả lời xong
            used, today = now - rest["start"], time.strftime("%Y-%m-%d")
            if used >= rest["next_tired"]:
                rest.update(next_tired=used + 3600, night=today)  # nhắc một câu thôi, không nhắc đêm khuya ngay sau
                char.say(pick("tired", h=int(used // 3600)), YAWN_EMOTE)
            elif time.localtime().tm_hour in NIGHT_HOURS and rest["night"] != today:
                rest.update(night=today, next_tired=max(rest["next_tired"], used + 3600))
                char.say(pick("night"), YAWN_EMOTE)
        char.root.after(2000, self.check_rest)

    def check_system(self):
        """Pin dưới LOW_BATTERY% mà không cắm sạc: nhắc một lần (cắm sạc / pin lên lại thì reset). Mất mạng / có lại mạng."""
        char, power = self.char, self.power
        percent, plugged = battery()
        if percent is not None and percent < LOW_BATTERY and not plugged:
            if not power["low"] and not char.asking:
                power["low"] = True
                char.say(pick("battery", p=percent), "soc")
        elif plugged or (percent or 0) >= LOW_BATTERY + 5:
            power["low"] = False
        net = online()
        if net != power["online"] and not char.asking:
            power["online"] = net
            char.say(*((pick("net_back"), "lap_lanh") if net else (pick("net_lost"), "buon")))
        self.check_lunch()
        char.root.after(30000, self.check_system)

    def check_lunch(self):
        """11h-13h30, biết món bạn thích: rủ đi ăn món đó, mỗi ngày một lần, lúc đang rảnh (không nói / hỏi / ngủ)."""
        char, now, today = self.char, time.localtime(), date.today()
        if self.lunch == today or not (11 * 60 <= now.tm_hour * 60 + now.tm_min <= 13 * 60 + 30):
            return
        if char.talking or char.asking or char.thinking or char.playing or self.state.sleeping.is_set():
            return
        memory = load_memory()
        food = favorite_food(memory)
        self.lunch = today
        if food:
            name = name_from(memory)
            char.say(pick("lunch", food=food[0], n=f" {name}" if name else ""), "lap_lanh")
