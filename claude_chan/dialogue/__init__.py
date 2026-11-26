"""Chọn câu nói: câu ngẫu nhiên theo tình huống, câu chào theo giờ, ngày đặc biệt, tên người dùng trong ký ức."""
import random
import re
from datetime import date

from ..core.config import LINES, LUNAR


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
