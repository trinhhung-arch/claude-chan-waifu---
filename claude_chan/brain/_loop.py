"""Luồng chạy nền: cứ một lúc nhìn màn hình rồi bình luận, có câu hỏi thì trả lời ngay."""
import queue
import random
import sys
import threading
import time
from collections import deque

from ..core.config import ANSWER_MODEL, ANSWER_ON, CHAT_EMOTES, COMMENT_ON, GAME_INTERVAL, HANDS_OFF_SECONDS, HISTORY_TURNS, INTERVAL, MOCK, TITLE, tr
from ..desktop import active_title, fullscreen, idle_seconds
from ..dialogue import pick
from ..memory import remember
from ..vision import changed, is_private, screenshot, to_jpeg
from ._api import make_client
from ._client import chat
from ._feed import taste
from ._parse import quick_intent


class Cancelled(Exception):
    """Lượt bình luận bị bỏ giữa chừng vì người dùng vừa hỏi."""


def comment(prompt, jpeg, asks):
    """Nhờ model bình luận ảnh màn hình, nhưng có câu hỏi mới thì bỏ ngay: cắt kết nối (Ollama thấy client ngắt thì
    dừng viết, rảnh trả lời luôn), khỏi bắt người dùng chờ hết câu bình luận 20-50 giây mà sau đó cũng không hiện."""
    client, done = make_client(180), threading.Event()  # kết nối riêng cho lượt này, cắt được

    def watch():
        while not done.wait(0.2):
            if not asks.empty():
                client._client.close()  # httpx bên trong client: đóng là lệnh đang chờ ở luồng kia thoát ra ngay
                return

    threading.Thread(target=watch, daemon=True).start()
    try:
        return chat(client, prompt, jpeg)[:2]  # bình luận màn hình: không học, không nhắc
    except Exception:
        if not asks.empty():
            raise Cancelled from None
        raise
    finally:
        done.set()


def worker(out, asks, state):
    """out nhận (lời, emote) = bình luận, hoặc (lời, emote, True, nhắc, tập trung) = trả lời câu hỏi (hiện cả khi đang
    tạm dừng), nhắc = (phút, việc) nếu nhờ nhắc việc, tập trung = số phút nếu người dùng nói sắp làm việc bao lâu.
    asks: câu người dùng hỏi.  state: trạng thái chung (tạm dừng, ngủ, ẩn, cửa sổ đang mở)."""
    client = make_client(180)
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
        title = state.seen_title if title == TITLE else title  # đang bấm vào nhân vật thì xét cửa sổ trước đó
        if isinstance(question, tuple) and question[0] == "feed":  # ("feed", [đường dẫn]): được cho "ăn" file / ảnh
            line, emote = taste(question[1], lambda p, jpeg, model: chat(client, p, jpeg, model=model)[:2])
            out.put((line, emote, True, None, None))
            continue
        if question is not None:
            # ("clip", chữ): hỏi về đoạn vừa copy -> chỉ gửi chữ đó, không chụp màn hình, không học, không nhắc việc
            clip = isinstance(question, tuple)
            text, remind, focus = (question[1] if clip else question), None, None
            try:
                blind = clip or state.paused.is_set() or is_private(title)  # tạm dừng / riêng tư: trả lời mà không nhìn màn hình
                if clip:
                    prompt = ("Người dùng vừa copy đoạn dưới đây và nhờ bạn: nếu là code thì giải thích nó làm gì (và chỉ ra"
                              " lỗi nếu thấy), nếu là tiếng nước ngoài thì dịch sang tiếng Việt, còn lại thì tóm tắt ý chính."
                              f" Tối đa 3 câu ngắn, rồi chọn emote hợp cảm xúc.\n---\n{text}\n---")
                else:
                    # model trả lời (ANSWER_MODEL) không xem được ảnh: chỉ biết màn hình qua tên cửa sổ và câu vừa bình luận
                    prompt = (f'Người dùng hỏi bạn: "{text}". Trả lời đúng câu hỏi, tối đa 3 câu ngắn, rồi chọn emote hợp cảm xúc.'
                              + (" Lúc này bạn KHÔNG được xem màn hình, chỉ trả lời bằng hiểu biết của mình." if blind
                                 else f' Bạn không thấy màn hình lúc này, chỉ biết người dùng đang mở cửa sổ "{title}".'))
                    if recent:
                        prompt += " Những câu bạn vừa tự bình luận: " + " | ".join(recent)
                if MOCK:  # giả lập: "nhớ" -> ghi nhớ nguyên câu; nhắc việc / giờ tập trung hiểu bằng quick_intent
                    line = (f"(thử) Đoạn bạn copy: {text[:40]}..." if clip
                            else f"(thử) Bạn hỏi: {text}" + (" (mình không nhìn màn hình)" if blind else ""))
                    emote, facts = random.choice(CHAT_EMOTES), ([text] if not clip and "nhớ" in text.lower() else [])
                    remind, focus = (None, None) if clip else quick_intent(text)
                elif not ANSWER_ON:  # tắt trả lời (máy yếu / không có model chữ): chỉ hiểu nhắc việc, giờ tập trung
                    remind, focus = (None, None) if clip else quick_intent(text)
                    line, emote, facts = ((pick("no_model_ok"), "nhay_mat_ok", []) if remind or focus
                                          else (pick("no_model"), "buon", []))
                else:
                    line, emote, facts, remind, focus = chat(client, prompt, None, list(history), learn=not clip,
                                                             model=ANSWER_MODEL)
                if clip and (MOCK or ANSWER_ON):  # giải thích / dịch đoạn vừa copy luôn là lúc giải thích: kính mọt sách
                    emote = "mot_sach"
                history.extend([{"role": "user", "content": f"[đoạn vừa copy] {text[:300]}" if clip else text},
                                {"role": "assistant", "content": line}])
                remember(facts)  # nhớ lặng lẽ, không thêm "(Mình nhớ rồi nha!)" vào câu trả lời
                at = lambda minutes: time.strftime('%H:%M', time.localtime(time.time() + minutes * 60))
                if focus:  # phiên làm việc: app canh giờ + nhắc nghỉ, không cần thêm lời nhắc trùng
                    remind = None
                    line += tr(" (Bắt đầu tập trung {m} phút, xong lúc {t})").format(m=focus, t=at(focus))
                if remind:
                    line += tr(" (Mình sẽ nhắc lúc {t})").format(t=at(remind[0]))
            except Exception as e:
                print("Lỗi:", repr(e), file=sys.stderr)
                line, emote, remind, focus = pick("ask_fail"), "buon", None, None
            out.put((line, emote, True, remind, focus))
            continue
        # đang ngủ (người dùng rời máy) hoặc bị ẩn xuống khay thì không chụp, máy chạy model đỡ tốn GPU;
        # vừa có câu hỏi (nhân vật đang nghĩ) thì không chụp, không bình luận: trả lời trước đã
        # tắt bình luận (máy yếu / không có model đọc ảnh): không bao giờ chụp màn hình
        if (MOCK or COMMENT_ON) and not (state.paused.is_set() or state.sleeping.is_set() or state.hidden.is_set()
                                        or state.dragging.is_set() or not asks.empty()):
            if idle_seconds() < HANDS_OFF_SECONDS:  # đang gõ / rê chuột: chưa chụp, 1 giây sau xem lại
                wait = 1
                continue
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
                    elif not asks.empty() or state.dragging.is_set():  # vừa có câu hỏi / bị kéo lúc đang chụp: bỏ ảnh này
                        pass
                    else:
                        jpeg = to_jpeg(img)
                        if MOCK:
                            line, emote = f"(thử) Ảnh màn hình {len(jpeg) // 1024}KB, mình thấy rồi nha!", random.choice(CHAT_EMOTES)
                        else:
                            prompt = "Người dùng đang làm gì trên màn hình? Nói một câu với họ và chọn emote hợp cảm xúc."
                            if recent:
                                prompt += " Những câu bạn vừa nói (đừng lặp lại): " + " | ".join(recent)
                            line, emote = comment(prompt, jpeg, asks)
                        last = img  # chỉ nhớ khi gửi thành công, lỗi thì lượt sau gửi lại
                        recent.append(line)
                        out.put((line, emote))
                        offline = False
            except Cancelled:  # người dùng vừa hỏi: trả lời ngay ở vòng sau, ảnh này lượt sau gửi lại nếu cần
                print("Bỏ lượt bình luận: có câu hỏi", file=sys.stderr)
            except Exception as e:  # máy chạy Ollama tắt, mất mạng, model chưa tải...
                print("Lỗi:", repr(e), file=sys.stderr)
                if not offline:  # báo một lần mỗi đợt mất kết nối, không nhắc lại mỗi lượt
                    out.put((pick("offline"), "buon"))
                offline = True


def start(state):
    """Chạy luồng nền -> (asks, out): bỏ câu hỏi vào asks (chuỗi, ("clip", chữ) để giải thích đoạn vừa copy, hoặc
    ("feed", [đường dẫn]) khi được kéo thả file vào người),
    lấy lời nói ra từ out (xem worker)."""
    asks, out = queue.Queue(), queue.Queue()
    threading.Thread(target=worker, args=(out, asks, state), daemon=True).start()
    return asks, out
