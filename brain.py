"""Nói chuyện với model trên Mac: lời nhắc hệ thống, đọc câu trả lời, vòng lặp nhìn màn hình / trả lời câu hỏi."""
import json
import queue
import random
import re
import sys
import time
from collections import deque

import ollama

from config import CHAT_EMOTES, EMOTE_GUIDE, GAME_INTERVAL, HISTORY_TURNS, HOST, INTERVAL, MOCK, MODEL, PERSONA, TITLE
from dialogue import pick
from memory import load_memory, remember
from desktop import active_title, changed, fullscreen, is_private, screenshot, to_jpeg

# Emote mới thêm mà chưa có mô tả thì model chỉ thấy tên
SYSTEM = PERSONA + "\n\nChọn emote khớp với cảm xúc của câu bạn nói:\n" + "\n".join(
    f"- {e}: {EMOTE_GUIDE.get(e, e.replace('_', ' '))}" for e in CHAT_EMOTES)


def parse(content):
    """Câu trả lời của model -> (lời nói, emote); emote lạ thì về mim_cuoi."""
    try:
        data = json.loads(content)
        line, emote = str(data.get("loi_noi", "")).strip(), data.get("emote")
    except (json.JSONDecodeError, AttributeError):
        line, emote = str(content).strip(), None
    return line or "...", emote if emote in CHAT_EMOTES else "mim_cuoi"


def parse_facts(content):
    """Lấy danh sách "ghi_nho" trong câu trả lời của model; hỏng thì coi như không có gì mới."""
    try:
        facts = json.loads(content).get("ghi_nho", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    if not isinstance(facts, list):
        return []
    return [" ".join(str(f).split())[:200] for f in facts if str(f).strip()][:5]


def parse_reminder(content):
    """"nhac_phut"/"nhac_viec" trong câu trả lời -> (phút, việc), hoặc None nếu không nhờ nhắc / số phút vô lý."""
    try:
        data = json.loads(content)
        minutes, what = int(data.get("nhac_phut") or 0), " ".join(str(data.get("nhac_viec") or "").split())
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return None
    return (minutes, what[:100] or "việc bạn nhờ") if 1 <= minutes <= 24 * 60 else None


def parse_focus(content):
    """"tap_trung_phut" -> số phút người dùng nói sẽ làm việc/học tập trung (1-240), không có thì None."""
    try:
        minutes = int(json.loads(content).get("tap_trung_phut") or 0)
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return None
    return minutes if 1 <= minutes <= 240 else None


def chat(client, prompt, jpeg=None, history=(), learn=False):
    """Gọi model -> (lời nói, emote, điều mới cần nhớ, lời nhờ nhắc (phút, việc) hoặc None, số phút tập trung hoặc None).
    history: các lượt hỏi-đáp trước (chỉ chữ).  learn=True (chỉ khi trả lời câu người dùng tự gõ, không học từ ảnh
    màn hình): model liệt kê điều mới đáng nhớ, lời nhờ nhắc việc, và phiên làm việc N phút nếu người dùng nói tới."""
    memory = load_memory()
    system = SYSTEM + ("\n\nNhững điều bạn nhớ về người dùng (dùng khi hợp lúc, đừng lần nào cũng nhắc):\n"
                       + "\n".join(f"- {m}" for m in memory) if memory else "")
    props = {"loi_noi": {"type": "string"}, "emote": {"type": "string", "enum": CHAT_EMOTES}}
    if learn:
        props["ghi_nho"] = {"type": "array", "items": {"type": "string"}}
        prompt += (' Trong "ghi_nho", liệt kê điều MỚI đáng nhớ lâu dài mà người dùng vừa tự nói về bản thân'
                   " (tên, sở thích, dự án lâu dài, ngày quan trọng như sinh nhật...), mỗi điều một câu ngắn;"
                   " không có gì mới thì để []. Không ghi việc tạm thời trong hôm nay (đang làm gì trong bao lâu,"
                   " hẹn giờ, lời nhắc), không ghi mật khẩu, số tài khoản, mã OTP.")
        props["nhac_phut"], props["nhac_viec"] = {"type": "integer"}, {"type": "string"}
        props["tap_trung_phut"] = {"type": "integer"}
        prompt += (f" Bây giờ là {time.strftime('%H:%M')}. Nếu người dùng nói sắp làm việc / học / code / tập trung"
                   ' trong một khoảng thời gian (vd "mình code 40 phút", "làm bài nửa tiếng", "học 1 tiếng"), điền'
                   ' "tap_trung_phut" = số phút đó và để "nhac_phut" = 0 (app tự canh giờ, hết giờ sẽ nhắc nghỉ).'
                   ' Còn nếu người dùng nhờ nhắc một việc khác sau một lúc hay vào một giờ trong 24 giờ tới, điền'
                   ' "nhac_phut" = số phút tính từ bây giờ và "nhac_viec" = việc cần nhắc. Không có thì để 0 và "".')
    msg = {"role": "user", "content": prompt}
    if jpeg:
        msg["images"] = [jpeg]
    r = client.chat(
        model=MODEL,
        messages=[{"role": "system", "content": system}, *history, msg],
        format={  # Ollama ép model trả đúng JSON này, emote chỉ được nằm trong danh sách
            "type": "object",
            "properties": props,
            "required": list(props),
        },
        # num_ctx: mặc định Ollama chỉ đọc 2-4 nghìn token, ký ức + lịch sử + ảnh sẽ bị cắt mất phần đầu mà không báo
        options={"temperature": 0.8, "num_ctx": 8192},
        keep_alive="30m",
    )
    content = r.message.content
    if not learn:
        return (*parse(content), [], None, None)
    return (*parse(content), parse_facts(content), parse_reminder(content), parse_focus(content))


def worker(out, paused, asks, seen, sleeping, hidden):
    """out nhận (lời, emote) = bình luận, hoặc (lời, emote, True, nhắc, tập trung) = trả lời câu hỏi (hiện cả khi đang
    tạm dừng), nhắc = (phút, việc) nếu nhờ nhắc việc, tập trung = số phút nếu người dùng nói sắp làm việc bao lâu.
    asks: câu người dùng hỏi.  seen["title"]: tiêu đề cửa sổ khác gần nhất (khi người dùng đang bấm vào nhân vật)."""
    client = ollama.Client(host=HOST, timeout=180)
    recent = deque(maxlen=3)  # câu bình luận gần nhất
    history = deque(maxlen=HISTORY_TURNS * 2)  # các lượt hỏi-đáp gần nhất, chỉ trong RAM
    last = None  # ảnh đã gửi model lần gần nhất
    hiding = False  # đang ở cửa sổ riêng tư
    offline = False  # đã báo mất kết nối chưa
    wait = 3
    while True:
        try:  # chờ tới lượt nhìn màn hình, nhưng có câu hỏi thì trả lời ngay
            question = asks.get(timeout=wait)
        except queue.Empty:
            question = None
        # chơi game / xem video toàn màn hình: nói thưa hơn cho đỡ phiền
        wait = (15 if MOCK else GAME_INTERVAL) if fullscreen() else (5 if MOCK else INTERVAL)
        title = active_title()
        title = seen["title"] if title == TITLE else title  # đang bấm vào nhân vật thì xét cửa sổ trước đó
        if question is not None:
            # ("clip", chữ): hỏi về đoạn vừa copy -> chỉ gửi chữ đó, không chụp màn hình, không học, không nhắc việc
            clip = isinstance(question, tuple)
            text, remind, focus = (question[1] if clip else question), None, None
            try:
                blind = clip or paused.is_set() or is_private(title)  # tạm dừng / riêng tư: trả lời mà không nhìn màn hình
                if clip:
                    prompt = ("Người dùng vừa copy đoạn dưới đây và nhờ bạn: nếu là code thì giải thích nó làm gì (và chỉ ra"
                              " lỗi nếu thấy), nếu là tiếng nước ngoài thì dịch sang tiếng Việt, còn lại thì tóm tắt ý chính."
                              f" Tối đa 3 câu ngắn, rồi chọn emote hợp cảm xúc.\n---\n{text}\n---")
                else:
                    prompt = (f'Người dùng hỏi bạn: "{text}". Trả lời đúng câu hỏi, tối đa 3 câu ngắn, rồi chọn emote hợp cảm xúc.'
                              + (" Lúc này bạn KHÔNG được xem màn hình, chỉ trả lời bằng hiểu biết của mình." if blind
                                 else " Dựa vào ảnh màn hình nếu câu hỏi liên quan."))
                    if recent:
                        prompt += " Những câu bạn vừa tự bình luận: " + " | ".join(recent)
                if MOCK:  # giả lập: "nhớ" -> ghi nhớ nguyên câu; "nhắc ... N phút" -> hẹn; "làm/học/code ... N phút" -> tập trung
                    line = (f"(thử) Đoạn bạn copy: {text[:40]}..." if clip
                            else f"(thử) Bạn hỏi: {text}" + (" (mình không nhìn màn hình)" if blind else ""))
                    emote, facts = random.choice(CHAT_EMOTES), ([text] if not clip and "nhớ" in text.lower() else [])
                    m, low = re.search(r"(\d+)\s*phút", text), text.lower()
                    if m and not clip and "nhắc" in low:
                        remind = (int(m.group(1)), text)
                    elif m and not clip and any(w in low for w in ("tập trung", "làm", "học", "code")):
                        focus = int(m.group(1))
                else:
                    line, emote, facts, remind, focus = chat(client, prompt, None if blind else to_jpeg(screenshot()),
                                                             list(history), learn=not clip)
                if clip:  # giải thích / dịch đoạn vừa copy luôn là lúc giải thích: đeo kính mọt sách
                    emote = "mot_sach"
                history.extend([{"role": "user", "content": f"[đoạn vừa copy] {text[:300]}" if clip else text},
                                {"role": "assistant", "content": line}])
                if remember(facts):
                    line += " (Mình nhớ rồi nha!)"
                at = lambda minutes: time.strftime('%H:%M', time.localtime(time.time() + minutes * 60))
                if focus:  # phiên làm việc: app canh giờ + nhắc nghỉ, không cần thêm lời nhắc trùng
                    remind = None
                    line += f" (Bắt đầu tập trung {focus} phút, xong lúc {at(focus)})"
                if remind:
                    line += f" (Mình sẽ nhắc lúc {at(remind[0])})"
            except Exception as e:
                print("Lỗi:", repr(e), file=sys.stderr)
                line, emote, remind, focus = pick("ask_fail"), "buon", None, None
            out.put((line, emote, True, remind, focus))
            continue
        # đang ngủ (người dùng rời máy) hoặc bị ẩn xuống khay thì không chụp, Mac đỡ tốn GPU
        if not (paused.is_set() or sleeping.is_set() or hidden.is_set()):
            try:
                if is_private(title):  # kiểm tra ngay trước lúc chụp; riêng tư thì không chụp gì cả
                    if not hiding:
                        out.put((pick("private"), "xau_ho"))
                    hiding = True
                else:
                    hiding = False
                    img = screenshot()
                    if not changed(img, last):
                        print("Bỏ qua: màn hình gần như không đổi", file=sys.stderr)
                    else:
                        jpeg = to_jpeg(img)
                        if MOCK:
                            line, emote = f"(thử) Ảnh màn hình {len(jpeg) // 1024}KB, mình thấy rồi nha!", random.choice(CHAT_EMOTES)
                        else:
                            prompt = "Người dùng đang làm gì trên màn hình? Nói một câu với họ và chọn emote hợp cảm xúc."
                            if recent:
                                prompt += " Những câu bạn vừa nói (đừng lặp lại): " + " | ".join(recent)
                            line, emote, *_ = chat(client, prompt, jpeg)  # bình luận màn hình: không học, không nhắc
                        last = img  # chỉ nhớ khi gửi thành công, lỗi thì lượt sau gửi lại
                        recent.append(line)
                        out.put((line, emote))
                        offline = False
            except Exception as e:  # Mac tắt, mất mạng, model chưa tải...
                print("Lỗi:", repr(e), file=sys.stderr)
                if not offline:  # báo một lần mỗi đợt mất kết nối, không nhắc lại mỗi lượt
                    out.put((pick("offline"), "buon"))
                offline = True
