"""Gọi model qua Ollama (máy này hoặc máy khác trong mạng): lời dặn hệ thống + ký ức + lịch sử, ép trả JSON đúng khuôn."""
import time

from ..core.config import CHAT_EMOTES, EMOTE_GUIDE, LANGUAGE, PERSONA, VISION_MODEL
from ..memory import load_memory
from ._parse import parse, parse_explaining, parse_facts, parse_focus, parse_reminder

# Emote mới thêm mà chưa có mô tả thì model chỉ thấy tên
SYSTEM = PERSONA + "\n\nChọn emote khớp với cảm xúc của câu bạn nói (chỉ ghi vào trường emote, KHÔNG viết tên emote vào câu nói):\n" + "\n".join(
    f"- {e}: {EMOTE_GUIDE.get(e, e.replace('_', ' '))}" for e in CHAT_EMOTES)


def chat(client, prompt, jpeg=None, history=(), learn=False, model=VISION_MODEL):
    """Gọi model -> (lời nói, emote, điều mới cần nhớ, lời nhờ nhắc (phút, việc) hoặc None, số phút tập trung hoặc None).
    history: các lượt hỏi-đáp trước (chỉ chữ).  learn=True (chỉ khi trả lời câu người dùng tự gõ, không học từ ảnh
    màn hình): model liệt kê điều mới đáng nhớ, lời nhờ nhắc việc, và phiên làm việc N phút nếu người dùng nói tới.
    model: model trên Ollama; gpt-oss chỉ đọc chữ (đừng đưa jpeg) và được bảo nghĩ ít cho nhanh."""
    memory = load_memory()
    system = SYSTEM + ("\n\nNhững điều bạn nhớ về người dùng (dùng khi hợp lúc, đừng lần nào cũng nhắc):\n"
                       + "\n".join(f"- {m}" for m in memory) if memory else "")
    props = {"loi_noi": {"type": "string"}, "emote": {"type": "string", "enum": CHAT_EMOTES}}
    if learn:
        # đứng trước emote: model quyết "có đang giải thích không" rồi mới chọn emote; true thì app tự đeo kính mọt sách
        props = {"loi_noi": props["loi_noi"], "giai_thich": {"type": "boolean"}, "emote": props["emote"]}
        prompt += (' "giai_thich" = true nếu câu trả lời đang giải thích, định nghĩa, dạy hay chỉ cách làm một điều gì'
                   ' (kiến thức, code, từ ngữ, cách dùng...); chỉ chào hỏi, đùa, an ủi, nhận lời nhắc thì false.')
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
    if LANGUAGE == "en":  # lời dặn viết tiếng Việt, nhắc lại để câu nói ra tiếng Anh
        prompt += " Write loi_noi in English." + (' When reminding, "nhac_viec" must name the task in English, e.g. "drink water".' if learn else "")
    msg = {"role": "user", "content": prompt}
    if jpeg:
        msg["images"] = [jpeg]
    r = client.chat(
        model=model,
        messages=[{"role": "system", "content": system}, *history, msg],
        format={  # Ollama ép model trả đúng JSON này, emote chỉ được nằm trong danh sách
            "type": "object",
            "properties": props,
            "required": list(props),
        },
        # num_ctx: mặc định Ollama chỉ đọc 2-4 nghìn token, ký ức + lịch sử + ảnh sẽ bị cắt mất phần đầu mà không báo
        options={"temperature": 0.8, "num_ctx": 8192},
        keep_alive="30m",
        # gpt-oss luôn "nghĩ" trước khi trả lời; mức low cho nhanh, câu nghĩ nằm riêng (message.thinking), không lẫn vào lời nói
        **({"think": "low"} if model.startswith("gpt-oss") else {}),
    )
    content = r.message.content
    if not learn:
        return (*parse(content), [], None, None)
    line, emote = parse(content)
    if parse_explaining(content):  # giải thích điều gì thì luôn là mọt sách, không để model tự chọn emote khác
        emote = "mot_sach"
    return line, emote, parse_facts(content), parse_reminder(content), parse_focus(content)
