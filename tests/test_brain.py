"""brain: đọc JSON của model (lời, emote, ký ức, nhắc việc, tập trung) và gói tin gửi model."""
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from claude_chan import memory
from claude_chan.brain import SYSTEM, chat, parse, parse_explaining, parse_facts, parse_focus, parse_reminder
from claude_chan.core.config import CHAT_EMOTES, EMOTE_GUIDE

# nhờ nhắc việc: chỉ nhận số phút hợp lý (1 phút tới 24 giờ)
assert parse_reminder('{"nhac_phut": 15, "nhac_viec": " uống   nước "}') == (15, "uống nước")
assert parse_reminder('{"nhac_phut": 30, "nhac_viec": ""}') == (30, "việc bạn nhờ")
assert parse_reminder('{"nhac_phut": "45", "nhac_viec": "họp"}') == (45, "họp")  # số dạng chữ
for bad in ('{"nhac_phut": 0, "nhac_viec": ""}', '{"nhac_phut": -5}', '{"nhac_phut": 99999}', '{"nhac_phut": "abc"}',
            '{"loi_noi": "hi"}', '{"nhac_phut": null}', "hỏng", "[1]"):
    assert parse_reminder(bad) is None, bad

assert parse_facts('{"loi_noi": "ok", "emote": "soc", "ghi_nho": ["  Thích   mèo ", "", 5]}') == ["Thích mèo", "5"]
assert parse_facts('{"ghi_nho": "không phải list"}') == [] and parse_facts("hỏng") == [] and parse_facts("[1]") == []

# "mình code 40 phút": số phút tập trung hợp lý 1-240
assert parse_focus('{"tap_trung_phut": 40}') == 40 and parse_focus('{"tap_trung_phut": "30"}') == 30
for bad in ('{"tap_trung_phut": 0}', '{"tap_trung_phut": 500}', '{"tap_trung_phut": null}', '{"loi_noi": "hi"}', "hỏng", "[1]"):
    assert parse_focus(bad) is None, bad

assert "- bi_keo" not in SYSTEM and parse('{"loi_noi": "hi", "emote": "bi_keo"}') == ("hi", "mim_cuoi")
assert parse('{"loi_noi": " Code đẹp ghê! ", "emote": "lap_lanh"}') == ("Code đẹp ghê!", "lap_lanh")
assert parse('{"loi_noi": "hi", "emote": "khong_co"}') == ("hi", "mim_cuoi")  # emote lạ
assert parse("không phải json") == ("không phải json", "mim_cuoi")
assert parse('{"emote": "buon"}') == ("...", "buon")
assert parse("[1, 2]") == ("[1, 2]", "mim_cuoi")  # JSON nhưng không phải object

sent = {}


class FakeClient:
    def chat(self, **kw):
        sent.update(kw)
        return SimpleNamespace(message=SimpleNamespace(
            content='{"loi_noi": "Lỗi đỏ kìa!", "emote": "soc", "ghi_nho": ["Đang làm logo waifu"],'
                    ' "nhac_phut": 15, "nhac_viec": "uống nước"}'))


saved = memory.MEMORY_FILE
memory.MEMORY_FILE = Path(tempfile.mkdtemp()) / "ky_uc.txt"  # ký ức giả, không đụng ký ức thật
memory.MEMORY_FILE.write_text("Bạn tên Hùng\n", encoding="utf-8")
try:
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
    assert sent["format"]["required"] == ["loi_noi", "giai_thich", "emote", "ghi_nho", "nhac_phut", "nhac_viec",
                                          "tap_trung_phut"]
    assert "giai_thich" in sent["messages"][3]["content"]  # có dặn model khi nào là đang giải thích
    assert "Không ghi việc tạm thời" in sent["messages"][3]["content"]  # "đang code 20 phút" không vào ký ức
    assert "Bây giờ là " in sent["messages"][3]["content"]  # model cần giờ để đổi "lúc 3 giờ chiều" ra số phút
finally:
    memory.MEMORY_FILE = saved

# hai model: bình luận màn hình bằng model có mắt, trả lời câu hỏi bằng model chữ (gpt-oss: nghĩ ít cho nhanh)
from claude_chan.core.config import ANSWER_MODEL, VISION_MODEL
saved = memory.MEMORY_FILE
memory.MEMORY_FILE = Path(tempfile.mkdtemp()) / "ky_uc.txt"
try:
    chat(FakeClient(), "xem màn hình", b"jpg")
    assert sent["model"] == VISION_MODEL and "think" not in sent
    chat(FakeClient(), "mấy giờ rồi", history=[], learn=True, model=ANSWER_MODEL)
    assert sent["model"] == ANSWER_MODEL and "images" not in sent["messages"][-1]
    assert sent["think"] == "low" if ANSWER_MODEL.startswith("gpt-oss") else "think" not in sent
finally:
    memory.MEMORY_FILE = saved

# đang giải thích thì luôn đeo kính mọt sách, model chọn emote gì cũng vậy
assert parse_explaining('{"giai_thich": true}') and not parse_explaining('{"giai_thich": false}')
assert not parse_explaining('{"giai_thich": "true"}') and not parse_explaining("hỏng") and not parse_explaining("[1]")


class ExplainClient:
    def __init__(self, explaining):
        self.explaining = explaining

    def chat(self, **kw):
        return SimpleNamespace(message=SimpleNamespace(content='{"loi_noi": "List comprehension là...", "giai_thich": '
                                                               + ("true" if self.explaining else "false")
                                                               + ', "emote": "mim_cuoi"}'))


saved = memory.MEMORY_FILE
memory.MEMORY_FILE = Path(tempfile.mkdtemp()) / "ky_uc.txt"
try:
    assert chat(ExplainClient(True), "list comprehension là gì", learn=True)[1] == "mot_sach"
    assert chat(ExplainClient(False), "chào bạn", learn=True)[1] == "mim_cuoi"
finally:
    memory.MEMORY_FILE = saved

# tên emote lọt vào lời nói thì bỏ đi, không hiện lên bong bóng
assert parse('{"loi_noi": "Chăm chỉ quá! Hãy tiếp tục nha! :co_vu:", "emote": "co_vu"}') == (
    "Chăm chỉ quá! Hãy tiếp tục nha!", "co_vu")
assert parse('{"loi_noi": "Hay ghê (lap_lanh) nè", "emote": "lap_lanh"}')[0] == "Hay ghê nè"
assert parse('{"loi_noi": "Cố lên [emote: co_vu]!", "emote": "co_vu"}')[0] == "Cố lên!"
assert parse('{"loi_noi": "Ok :thumbs_up: luôn", "emote": "mim_cuoi"}')[0] == "Ok luôn"
assert parse('{"loi_noi": "Biến my_var và hàm buon() vẫn giữ", "emote": "mim_cuoi"}')[0] == "Biến my_var và hàm buon() vẫn giữ"
assert parse('{"loi_noi": ":co_vu:", "emote": "co_vu"}')[0] == "..."
assert parse('{"loi_noi": "Ui :soc: thật luôn (buon)", "emote": "soc"}')[0] == "Ui thật luôn"
assert parse('{"loi_noi": "Hay quá co_vu", "emote": "co_vu"}')[0] == "Hay quá"

# API trên mạng theo chuẩn OpenAI: ảnh gửi dạng data URL, ép khuôn JSON, key ở header, 400 thì lùi dần, lỗi khác thì báo
import httpx
from claude_chan.brain import ApiClient

calls = []


def fake_api(request):
    body = json.loads(request.content) if request.content else None
    calls.append((request.method, request.url.path, request.headers.get("authorization"), body))
    if request.url.path.endswith("/models"):
        return httpx.Response(200, json={"data": [{"id": "gpt-b"}, {"id": "gpt-a"}]})
    if body["model"] == "kho-tinh":  # model khó tính: không nhận temperature, không nhận khuôn JSON chi tiết
        if "temperature" in body or body.get("response_format", {}).get("type") == "json_schema":
            return httpx.Response(400, json={"error": "unsupported"})
    if body["model"] == "sai-key":
        return httpx.Response(401, json={"error": "bad key"})
    return httpx.Response(200, json={"choices": [{"message": {"content": '{"loi_noi": "Chào nha", "emote": "mim_cuoi"}'}}]})


api = ApiClient("https://api.vd.com/v1/", "sk-thu", 5)
api._client = httpx.Client(transport=httpx.MockTransport(fake_api), headers=api._client.headers)
r = api.chat(model="vd-mo", messages=[{"role": "system", "content": "dặn"}, {"role": "user", "content": "xem", "images": [b"jpg"]}],
             format={"type": "object", "properties": {"loi_noi": {}, "emote": {}}}, options={"temperature": 0.8},
             keep_alive="30m", think="low")
method, path, auth, body = calls[-1]
assert r.message.content.startswith('{"loi_noi": "Chào nha"') and (method, path, auth) == ("POST", "/v1/chat/completions", "Bearer sk-thu")
assert body["messages"][0] == {"role": "system", "content": "dặn"} and body["temperature"] == 0.8
assert body["messages"][1]["content"] == [{"type": "text", "text": "xem"},
                                          {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,anBn"}}]
assert body["response_format"]["type"] == "json_schema" and "keep_alive" not in body and "think" not in body
calls.clear()
api.chat(model="kho-tinh", messages=[{"role": "user", "content": "hi"}], format={"properties": {"loi_noi": {}}},
         options={"temperature": 0.8})
assert len(calls) == 3 and calls[-1][3]["response_format"] == {"type": "json_object"} and "temperature" not in calls[-1][3]
assert "loi_noi" in calls[-1][3]["messages"][0]["content"]  # nhắc tên trường JSON khi chỉ ép "trả JSON"
try:
    api.chat(model="sai-key", messages=[{"role": "user", "content": "hi"}])
    raise AssertionError("phải báo lỗi")
except RuntimeError as e:
    assert "401" in str(e)
assert api.models() == ["gpt-a", "gpt-b"]
saved = memory.MEMORY_FILE
memory.MEMORY_FILE = Path(tempfile.mkdtemp()) / "ky_uc.txt"
try:  # cả đường chat() của app chạy được với ApiClient
    assert chat(api, "xem màn hình", b"jpg", model="vd-mo")[:2] == ("Chào nha", "mim_cuoi")
finally:
    memory.MEMORY_FILE = saved

# không có model (máy yếu): vẫn hiểu nhờ nhắc việc và giờ tập trung bằng quy tắc đơn giản
from claude_chan.brain import quick_intent
assert quick_intent("15 phút nữa nhắc mình uống nước nhé") == ((15, "uống nước"), None)
assert quick_intent("nhắc tôi gọi mẹ sau 2 tiếng nha") == ((120, "gọi mẹ"), None)
assert quick_intent("mình code 40 phút") == (None, 40) and quick_intent("học nửa tiếng") == (None, 30)
assert quick_intent("làm bài 1 tiếng") == (None, 60)
# tiếng Anh (tắt AI mà để giao diện tiếng Anh)
assert quick_intent("remind me to drink water in 15 minutes") == ((15, "drink water"), None)
assert quick_intent("In 2 hours remind me to call mom please") == ((120, "call mom"), None)
assert quick_intent("remind me in 30 mins to stretch!") == ((30, "stretch"), None)
assert quick_intent("remind me to eat in half an hour") == ((30, "eat"), None)
assert quick_intent("I'll code for 40 minutes") == (None, 40) and quick_intent("study for an hour") == (None, 60)
assert quick_intent("focus 25 min") == (None, 25)
for q in ("Python là gì", "nhắc mình 0 phút", "code 500 phút", "hôm nay 3 giờ chiều trời đẹp", "what is python",
          "remind me 0 minutes", "my network took 5 minutes", "it's 3 hours past noon"):
    assert quick_intent(q) == (None, None), q

# cho "ăn" file: ảnh thì gửi kèm ảnh cho model đọc ảnh, file khác chỉ gửi tên / loại cho model chữ, lỗi thì câu có sẵn
from PIL import Image
from claude_chan.brain import taste
import claude_chan.brain._feed as feed_mod
calls = []
fake_ask = lambda prompt, jpeg, model: (calls.append((prompt, jpeg, model)), ("Ngon!", "lap_lanh"))[1]
with tempfile.TemporaryDirectory() as d:
    Image.new("RGB", (40, 30), "red").save(Path(d) / "meo.png")
    (Path(d) / "bao_cao.docx").write_bytes(b"x" * 2048)
    feed_mod.COMMENT_ON = feed_mod.ANSWER_ON = True
    assert taste([str(Path(d) / "meo.png")], fake_ask) == ("Ngon!", "lap_lanh")
    assert calls[-1][1][:2] == b"\xff\xd8" and calls[-1][2] == VISION_MODEL and "meo.png" in calls[-1][0]
    taste([str(Path(d) / "bao_cao.docx"), str(Path(d) / "meo.png")], fake_ask)
    assert calls[-1][1] is None and calls[-1][2] == ANSWER_MODEL and "bao_cao.docx" in calls[-1][0] and "2KB" in calls[-1][0]
    assert "kèm 1 cái nữa" in calls[-1][0]
    feed_mod.ANSWER_ON = False
    line, emote = taste([str(Path(d) / "bao_cao.docx")], fake_ask)
    assert "bao_cao.docx" in line or "docx" in line
    line, emote = taste([str(Path(d) / "khong_co.png")], fake_ask)  # file đã mất: không sập, nói câu nghẹn
    assert emote == "buon"
