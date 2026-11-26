"""Người dùng kéo thả file / ảnh vào nhân vật để "cho ăn": nếm thử rồi nói một câu."""
import random
import sys
from pathlib import Path

from PIL import Image

from ..core.config import ANSWER_MODEL, ANSWER_ON, CHAT_EMOTES, COMMENT_ON, MOCK, VISION_MODEL, tr
from ..dialogue import pick
from ..vision import to_jpeg

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def _size(path):
    n = path.stat().st_size
    return next(f"{n / k:.0f}{u}" for k, u in ((1 << 30, "GB"), (1 << 20, "MB"), (1 << 10, "KB"), (1, " byte")) if n >= k or k == 1)


def taste(paths, ask):
    """paths: các đường dẫn vừa thả vào (nếm cái đầu, nhắc số còn lại). ask(prompt, jpeg, model) -> (lời, emote) gọi model.
    Ảnh: model đọc ảnh nhìn rồi nhận xét (tắt bình luận thì không nhìn). File khác / thư mục: model chữ đoán từ tên và
    loại file, không đọc nội dung. Tắt model thì nói câu có sẵn. Trả về (lời, emote)."""
    p = Path(paths[0])
    more = f" (kèm {len(paths) - 1} cái nữa)" if len(paths) > 1 else ""
    kind = tr("thư mục") if p.is_dir() else (p.suffix.lower().lstrip(".") or tr("không đuôi"))
    try:
        if p.suffix.lower() in IMAGE_EXT and (MOCK or COMMENT_ON):
            if MOCK:
                return f"(thử) Măm măm... ảnh {p.name} ngon ghê!", random.choice(CHAT_EMOTES)
            img = Image.open(p).convert("RGB")  # gif: lấy khung đầu
            img.thumbnail((1024, 1024))
            prompt = (f'Người dùng vừa kéo thả bức ảnh "{p.name}"{more} vào người bạn để cho bạn "ăn". Nhìn ảnh rồi nói'
                      " một câu dí dỏm như vừa nếm một món: trong ảnh có gì, vị ra sao. Rồi chọn emote hợp cảm xúc.")
            return ask(prompt, to_jpeg(img), VISION_MODEL)
        if MOCK:
            return f"(thử) Măm măm... {kind} {p.name}{more}", random.choice(CHAT_EMOTES)
        if ANSWER_ON:
            what = "thư mục" if p.is_dir() else f"file loại {kind}, nặng {_size(p)}"
            prompt = (f'Người dùng vừa kéo thả {what} tên "{p.name}"{more} vào người bạn để cho bạn "ăn". Bạn KHÔNG đọc'
                      " được bên trong, chỉ biết tên và loại. Đoán xem nó là gì từ cái tên rồi nói một câu dí dỏm như vừa"
                      " nếm món đó. Rồi chọn emote hợp cảm xúc.")
            return ask(prompt, None, ANSWER_MODEL)
        return pick("eat_file", name=p.name, kind=kind), "le_luoi"
    except Exception as e:  # file bị xoá / khoá, ảnh hỏng, model lỗi...
        print("Lỗi nếm file:", repr(e), file=sys.stderr)
        return pick("eat_fail"), "buon"
