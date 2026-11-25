"""Chạy: python test_assistant.py"""
from PIL import Image, ImageDraw

import tempfile
from pathlib import Path
from types import SimpleNamespace

from datetime import date

import memory
from brain import SYSTEM, chat, parse, parse_facts, parse_focus, parse_reminder
from config import (APP_EMOTES, APPS, CHAT_EMOTES, EMOTE_GUIDE, EMOTES, FACING, IDLE_POSES, LINES, LUNAR,
                    MAX_MEMORY)
from desktop import active_title, battery, changed, fullscreen, idle_seconds, is_private, online, screenshot, to_jpeg
from dialogue import app_category, birthday_from, greeting, name_from, special_day
from memory import load_memory, log_line, remember

# nhờ nhắc việc: chỉ nhận số phút hợp lý (1 phút tới 24 giờ)
assert parse_reminder('{"nhac_phut": 15, "nhac_viec": " uống   nước "}') == (15, "uống nước")
assert parse_reminder('{"nhac_phut": 30, "nhac_viec": ""}') == (30, "việc bạn nhờ")
assert parse_reminder('{"nhac_phut": "45", "nhac_viec": "họp"}') == (45, "họp")  # số dạng chữ
for bad in ('{"nhac_phut": 0, "nhac_viec": ""}', '{"nhac_phut": -5}', '{"nhac_phut": 99999}', '{"nhac_phut": "abc"}',
            '{"loi_noi": "hi"}', '{"nhac_phut": null}', "hỏng", "[1]"):
    assert parse_reminder(bad) is None, bad

# tên trong ký ức, câu chào theo giờ
assert name_from(["Thích mèo", "Người dùng tên Hùng"]) == "Hùng" and name_from(["Mình tên là Lan"]) == "Lan"
assert name_from(["tên file là main.py"]) == "" and name_from([]) == ""  # chữ thường: không phải tên người
assert name_from(["Tên là Hùng"]) == "Hùng"  # model thật hay ghi kiểu này
assert greeting(8, "Hùng")[1] == "nhay_mat_ok" and greeting(8, "Hùng")[0] in [s.format(n=" Hùng") for s in LINES["morning"]]
assert greeting(8)[0] in [s.format(n="") for s in LINES["morning"]] and "{" not in greeting(8)[0]
# mọi câu trong LINES điền được tham số (bắt lỗi gõ nhầm {hh}...), câu chào nào cũng có chỗ cho tên
for key, lines in LINES.items():
    assert lines and all(isinstance(s.format(n=" Hùng", h=2, p=15, m=25, b=5, what="uống nước"), str) for s in lines), key
assert all("{n}" in s for k in ("morning", "noon", "afternoon", "evening", "late", "monday", "friday",
                                "birthday", "tet", "trung_thu") for s in LINES[k])
assert set(FACING) <= set(EMOTES) and set(FACING.values()) <= {"left", "right"}
assert set(APP_EMOTES) == set(APPS) == {"code", "game", "chat"} and set(APP_EMOTES.values()) <= set(EMOTES)
assert all(k in LINES for k in APPS)
# sinh nhật trong ký ức, ngày đặc biệt
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
assert all(date.fromisoformat(d) for k in LUNAR for d in LUNAR[k])
# loại app theo tiêu đề cửa sổ
assert app_category("assistant.py - waifu claude - Visual Studio Code") == "code"
assert app_category("Steam") == "game" and app_category("Zalo") == "chat" and app_category("Discord | #general") == "chat"
assert app_category("Slay the Spire 2", is_fullscreen=True) == "game"  # game toàn màn hình
assert app_category("Funny cats - YouTube - Google Chrome", is_fullscreen=True) is None  # video trình duyệt: không phải game
assert app_category("Slay the Spire 2") is None and app_category("") is None
assert [greeting(h)[1] for h in (12, 15, 20, 23, 2, 4)] == ["mim_cuoi", "le_luoi", "suy_tu", "buon_ngu", "buon_ngu", "buon_ngu"]
assert all(greeting(h)[1] in EMOTES for h in range(24)) and set(IDLE_POSES) <= set(EMOTES)
# pin, mạng: đọc được từ Windows, đúng kiểu
pct, plugged = battery()
assert (pct is None or 0 <= pct <= 100) and isinstance(plugged, bool) and isinstance(online(), bool)
print("máy này: pin", pct, "| cắm sạc", plugged, "| có mạng", online())

tmp = Path(tempfile.mkdtemp())
memory.MEMORY_FILE = tmp / "ky_uc.txt"  # test không đụng ký ức thật của bạn

# ký ức: thêm, bỏ trùng, bỏ bí mật, giữ MAX_MEMORY điều mới nhất, đọc lại chỗ người dùng tự sửa
assert load_memory() == [] and remember([]) == []
assert remember(["Bạn tên Hùng", "Bạn tên Hùng", "Thích game thẻ bài"]) == ["Bạn tên Hùng", "Thích game thẻ bài"]
assert remember(["Bạn tên Hùng"]) == []  # đã nhớ rồi
assert remember(["Mật khẩu wifi là abc123", "STK 0123 4567 89", "Số điện thoại 0912.345.678", "Thứ 6 nộp bài"]) == ["Thứ 6 nộp bài"]
assert load_memory() == ["Bạn tên Hùng", "Thích game thẻ bài", "Thứ 6 nộp bài"]
memory.MEMORY_FILE.write_text("# ghi chú\nBạn tên Hùng\n\nThích code Python\n", encoding="utf-8")  # người dùng tự sửa file
assert load_memory() == ["Bạn tên Hùng", "Thích code Python"]
remember([f"điều {i}" for i in range(40)])
mem = load_memory()
assert len(mem) == MAX_MEMORY and mem[-1] == "điều 39" and "Bạn tên Hùng" not in mem  # quên điều cũ nhất
memory.MEMORY_FILE.write_text("Bạn tên Hùng\n", encoding="utf-8")

assert parse_facts('{"loi_noi": "ok", "emote": "soc", "ghi_nho": ["  Thích   mèo ", "", 5]}') == ["Thích mèo", "5"]
assert parse_facts('{"ghi_nho": "không phải list"}') == [] and parse_facts("hỏng") == [] and parse_facts("[1]") == []

assert 0 <= idle_seconds() < 49 * 24 * 3600  # đọc được thời gian rời máy thật, không âm

# nhật ký: mỗi câu một dòng, 4 cột tab; câu nhiều dòng/tab bị gộp thành một dòng
with tempfile.TemporaryDirectory() as d:
    log = Path(d) / "nhat_ky.txt"
    log_line("bình luận", "soc", "Lỗi đỏ kìa!\nSửa đi\tnha", path=log)
    log_line("trả lời", "mot_sach", "Dòng 12 thiếu dấu ngoặc.", path=log)
    rows = [r.split("\t") for r in log.read_text(encoding="utf-8").splitlines()]
    assert [r[1:] for r in rows] == [["bình luận", "soc", "Lỗi đỏ kìa! Sửa đi nha"], ["trả lời", "mot_sach", "Dòng 12 thiếu dấu ngoặc."]]
    assert len(rows[0][0]) == 19  # 2026-11-25 01:20:33
log_line("x", "y", "z", path=Path(d) / "khong_ton_tai" / "a.txt")  # thư mục không có: không được làm sập

# mô tả emote khớp đúng 16 file, và model nhận được mô tả + ảnh + danh sách emote được phép
assert set(EMOTE_GUIDE) == set(CHAT_EMOTES), set(EMOTE_GUIDE) ^ set(CHAT_EMOTES)
sent = {}


class FakeClient:
    def chat(self, **kw):
        sent.update(kw)
        return SimpleNamespace(message=SimpleNamespace(
            content='{"loi_noi": "Lỗi đỏ kìa!", "emote": "soc", "ghi_nho": ["Đang làm logo waifu"],'
                    ' "nhac_phut": 15, "nhac_viec": "uống nước"}'))


# bình luận màn hình: có ảnh, có ký ức, KHÔNG học, KHÔNG nhắc việc
assert chat(FakeClient(), "xem màn hình", b"jpg") == ("Lỗi đỏ kìa!", "soc", [], None, None)
system, user = sent["messages"]
assert all(f"- {e}: {EMOTE_GUIDE[e]}" in system["content"] for e in CHAT_EMOTES)
assert "- Bạn tên Hùng" in system["content"]  # ký ức được gửi kèm
assert user["images"] == [b"jpg"] and sent["format"]["properties"]["emote"]["enum"] == CHAT_EMOTES
assert "ghi_nho" not in sent["format"]["properties"] and sent["options"]["num_ctx"] == 8192
# trả lời câu hỏi: gửi kèm lịch sử và giờ hiện tại, được học, được nhờ nhắc
hist = [{"role": "user", "content": "đây là gì"}, {"role": "assistant", "content": "logo đó"}]
assert chat(FakeClient(), "15 phút nữa nhắc mình uống nước", history=hist, learn=True) == (
    "Lỗi đỏ kìa!", "soc", ["Đang làm logo waifu"], (15, "uống nước"), None)
assert sent["messages"][1:3] == hist and "images" not in sent["messages"][3]  # không nhìn màn hình thì không gửi ảnh
assert sent["format"]["required"] == ["loi_noi", "emote", "ghi_nho", "nhac_phut", "nhac_viec", "tap_trung_phut"]
assert "Không ghi việc tạm thời" in sent["messages"][3]["content"]  # "đang code 20 phút" không vào ký ức
# "mình code 40 phút": số phút tập trung hợp lý 1-240
assert parse_focus('{"tap_trung_phut": 40}') == 40 and parse_focus('{"tap_trung_phut": "30"}') == 30
for bad in ('{"tap_trung_phut": 0}', '{"tap_trung_phut": 500}', '{"tap_trung_phut": null}', '{"loi_noi": "hi"}', "hỏng", "[1]"):
    assert parse_focus(bad) is None, bad
assert "Bây giờ là " in sent["messages"][3]["content"]  # model cần giờ để đổi "lúc 3 giờ chiều" ra số phút

assert len(EMOTES) == 18 and {"mim_cuoi", "xau_ho", "co_vu", "bi_keo"} <= set(EMOTES)
assert "bi_keo" not in CHAT_EMOTES and len(CHAT_EMOTES) == 17  # ảnh bị kéo: model không được chọn
assert "- bi_keo" not in SYSTEM and parse('{"loi_noi": "hi", "emote": "bi_keo"}') == ("hi", "mim_cuoi")
assert APP_EMOTES["code"] == "co_vu"  # mở code = bắt đầu làm bài: cổ vũ
assert "giải thích" in EMOTE_GUIDE["mot_sach"] and "co_vu" in EMOTE_GUIDE["mot_sach"]  # mọt sách = lúc giải thích
assert parse('{"loi_noi": " Code đẹp ghê! ", "emote": "lap_lanh"}') == ("Code đẹp ghê!", "lap_lanh")
assert parse('{"loi_noi": "hi", "emote": "khong_co"}') == ("hi", "mim_cuoi")  # emote lạ
assert parse("không phải json") == ("không phải json", "mim_cuoi")
assert parse('{"emote": "buon"}') == ("...", "buon")
assert parse("[1, 2]") == ("[1, 2]", "mim_cuoi")  # JSON nhưng không phải object
assert to_jpeg(screenshot())[:2] == b"\xff\xd8"  # ra đúng JPEG

# màn hình đổi hay không
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

# cửa sổ riêng tư
assert is_private("Vietcombank - Ngân hàng số - Google Chrome")
assert is_private("Đăng nhập - Facebook") and is_private("Trang mới - [InPrivate] - Microsoft Edge")
assert is_private("Sign in - Google Accounts") and is_private("Bitwarden")
assert not is_private("assistant.py - Visual Studio Code") and not is_private("YouTube - Google Chrome")
assert isinstance(active_title(), str) and isinstance(fullscreen(), bool)
print("ok")
