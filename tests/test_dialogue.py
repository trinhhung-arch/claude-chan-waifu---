"""dialogue: tên trong ký ức, câu chào theo giờ, sinh nhật, ngày đặc biệt."""
from datetime import date

from claude_chan.core.config import EMOTES, LINES
from claude_chan.dialogue import birthday_from, greeting, name_from, special_day

assert name_from(["Thích mèo", "Người dùng tên Hùng"]) == "Hùng" and name_from(["Mình tên là Lan"]) == "Lan"
assert name_from(["tên file là main.py"]) == "" and name_from([]) == ""  # chữ thường: không phải tên người
assert name_from(["Tên là Hùng"]) == "Hùng"  # model thật hay ghi kiểu này
assert greeting(8, "Hùng")[1] == "nhay_mat_ok" and greeting(8, "Hùng")[0] in [s.format(n=" Hùng") for s in LINES["morning"]]
assert greeting(8)[0] in [s.format(n="") for s in LINES["morning"]] and "{" not in greeting(8)[0]
assert [greeting(h)[1] for h in (12, 15, 20, 23, 2, 4)] == ["mim_cuoi", "le_luoi", "suy_tu", "buon_ngu", "buon_ngu", "buon_ngu"]
assert all(greeting(h)[1] in EMOTES for h in range(24))

assert birthday_from(["Thích mèo", "Sinh nhật ngày 12/5"]) == (12, 5)
assert birthday_from(["sinh nhật của mình là 3 tháng 11"]) == (3, 11) and birthday_from(["Sinh nhật 07-08"]) == (7, 8)
assert birthday_from(["Thích mèo"]) is None and birthday_from(["sinh nhật 40/13"]) is None
in_pool = lambda r, key: r is not None and r[0] in [x.format(n="") for x in LINES[key]]  # câu chào (không tên) thuộc nhóm key?
mem = ["Người dùng tên Hùng", "Sinh nhật ngày 12/5"]
assert special_day(date(2027, 5, 12), 23, mem, "Hùng")[1] == "phan_khich"  # sinh nhật: cả đêm cũng chúc
assert "Hùng" in special_day(date(2027, 5, 12), 9, mem, "Hùng")[0]
tet = [in_pool(special_day(date(2027, 2, d), 9, []), "tet") for d in (5, 6, 7, 8, 9)]
assert tet == [False, True, True, True, False], tet  # Tết 2027 = 6/2: chúc mùng 1, 2, 3
assert in_pool(special_day(date(2027, 9, 15), 20, []), "trung_thu")
assert in_pool(special_day(date(2026, 11, 23), 9, []), "monday")  # 23/11/2026 là thứ Hai
assert in_pool(special_day(date(2026, 11, 27), 9, []), "friday")  # 27/11/2026 là thứ Sáu
assert special_day(date(2026, 11, 23), 22, []) is None  # thứ Hai mà tối khuya: để câu chào theo giờ nhắc đi ngủ
assert special_day(date(2026, 11, 25), 9, []) is None  # thứ Tư bình thường
