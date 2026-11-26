"""core: cấu hình emote, câu thoại, loại app, mặt quay, lịch âm."""
from datetime import date

from claude_chan.core.config import APP_EMOTES, BLINK, APPS, CHAT_EMOTES, EMOTE_GUIDE, EMOTES, FACING, IDLE_POSES, LINES, LUNAR

# mọi câu trong LINES điền được tham số (bắt lỗi gõ nhầm {hh}...), câu chào nào cũng có chỗ cho tên
for key, lines in LINES.items():
    assert lines and all(isinstance(s.format(n=" Hùng", h=2, p=15, m=25, b=5, what="uống nước", name="a.txt", kind="txt", food="phở"), str) for s in lines), key
assert all("{n}" in s for k in ("morning", "noon", "afternoon", "evening", "late", "monday", "friday",
                                "birthday", "tet", "trung_thu") for s in LINES[k])
assert set(FACING) <= set(EMOTES) and set(FACING.values()) <= {"left", "right"}
assert FACING == {"bo": "left", "soc": "right", "suy_tu": "left", "dang_nghi": "left", "buon": "left", "mim_cuoi": "left",
                  "lap_lanh": "left"}  # đã kiểm bằng mắt: soc liếc phải, các emote mặt nghiêng 3/4 hướng trái
assert set(APP_EMOTES) == set(APPS) == {"code", "game", "chat"} and set(APP_EMOTES.values()) <= set(EMOTES)
assert all(k in LINES for k in APPS)
assert all(date.fromisoformat(d) for k in LUNAR for d in LUNAR[k])
assert set(IDLE_POSES) <= set(EMOTES)

# mô tả emote khớp đúng các emote model được chọn
assert set(EMOTE_GUIDE) == set(CHAT_EMOTES), set(EMOTE_GUIDE) ^ set(CHAT_EMOTES)
assert len(EMOTES) == 28 and {"mim_cuoi", "xau_ho", "co_vu", "bi_keo", "dang_nghi", "chong_mat", "ngap"} <= set(EMOTES)
# ảnh bị kéo / đang chờ / chóng mặt / ngáp / nhắm mắt chớp chỉ dùng trong lúc đó: model không chọn
special = {"bi_keo", "dang_nghi", "chong_mat", "ngap", "duoc_xoa", "phe_qua", "bo", *BLINK.values()}
assert not special & set(CHAT_EMOTES) and len(CHAT_EMOTES) == 17
assert set(BLINK) | set(BLINK.values()) <= set(EMOTES)
assert APP_EMOTES["code"] == "co_vu"  # mở code = bắt đầu làm bài: cổ vũ
assert "giải thích" in EMOTE_GUIDE["mot_sach"] and "co_vu" in EMOTE_GUIDE["mot_sach"]  # mọt sách = lúc giải thích

# cài đặt người dùng: kiểm giá trị nhập, đọc file đè lên mặc định, file hỏng / mục lạ thì giữ mặc định
import json
import tempfile
from pathlib import Path

from claude_chan.core.config import SETTINGS, coerce_setting, load_settings

assert coerce_setting("int", 10, 3600, " 45 ") == 45 and coerce_setting("pct", 0, 100, "30") == 0.3
assert coerce_setting("text", None, None, "  gpt-oss:20b ") == "gpt-oss:20b" and coerce_setting("bool", None, None, False) is False
for kind, lo, hi, bad in (("int", 10, 3600, "5"), ("int", 10, 3600, "4.5"), ("int", 10, 3600, "abc"), ("pct", 0, 100, "150"),
                          ("text", None, None, "  "), ("bool", None, None, "có")):
    try:
        coerce_setting(kind, lo, hi, bad)
        raise AssertionError((kind, bad))
    except ValueError:
        pass
assert all(len(s) == 6 and s[3] in ("text", "int", "pct", "bool", "choice", "secret") for s in SETTINGS)
# nhà cung cấp chỉ nhận giá trị trong danh sách; API key được để trống và lưu file thì mã hoá (DPAPI), đọc lại đúng
from claude_chan.core.config import protect, unprotect
assert coerce_setting("choice", ("ollama", "api"), None, "api") == "api" and coerce_setting("secret", None, None, " ") == ""
try:
    coerce_setting("choice", ("ollama", "api"), None, "khac")
    raise AssertionError("choice lạ")
except ValueError:
    pass
assert protect("") == "" and unprotect(protect("sk-thu 123")) == "sk-thu 123" and "sk-thu" not in protect("sk-thu 123")
assert unprotect("go-tay") == "go-tay"
with tempfile.TemporaryDirectory() as d:
    f = Path(d) / "cai_dat.json"
    into = {"INTERVAL": 45, "WALK": True, "PEEK_CHANCE": 0.15, "HOST": "http://a"}
    f.write_text(json.dumps({"INTERVAL": 60, "WALK": False, "PEEK_CHANCE": 0.4, "HOST": "  ", "LA": 1, "AWAY_MINUTES": 999,
                             "PROVIDER": "api", "API_KEY": protect("sk-bi-mat")}), encoding="utf-8")
    load_settings(f, into)
    assert into == {"INTERVAL": 60, "WALK": False, "PEEK_CHANCE": 0.4, "HOST": "http://a", "PROVIDER": "api",
                    "API_KEY": "sk-bi-mat"}  # HOST trống, 999 phút: bỏ qua; key mã hoá đọc ra đúng
    f.write_text("hỏng {", encoding="utf-8")
    load_settings(f, into)  # file hỏng: không sập, giữ nguyên
    load_settings(Path(d) / "khong_co.json", into)
    assert into["INTERVAL"] == 60

# tiếng Anh: đủ mọi câu thoại (cùng chỗ điền {..}), mọi nhãn cài đặt / nhóm đều có bản dịch, tr đổi theo LANGUAGE
import re
from claude_chan.core import _en, config
holes = lambda s: set(re.findall(r"{(\w+)}", s))
if config.LANGUAGE == "vi":  # máy đang để tiếng Anh thì config.LINES đã là bản Anh, khỏi so
    assert set(_en.LINES) == set(config.LINES)
    for key in config.LINES:
        allowed = set().union(*(holes(s) for s in config.LINES[key]))
        assert _en.LINES[key] and all(holes(s) <= allowed for s in _en.LINES[key]), key
for key, label, group, *_ in config.SETTINGS:
    assert label in _en.UI and group in _en.UI, key
old = config.LANGUAGE
config.LANGUAGE = "en"
assert config.tr("Đóng") == "Close" and config.tr("chưa dịch") == "chưa dịch"
assert config.tr("Tập trung {m} phút").format(m=25) == "Focus 25 minutes"
config.LANGUAGE = "vi"
assert config.tr("Đóng") == "Đóng"
config.LANGUAGE = old
