"""Ký ức lâu dài (ky_uc.txt) và nhật ký câu nói (nhat_ky.txt)."""
import re
import sys
import time

from ..core.config import FOOD_EMOJI, LOG_FILE, MAX_MEMORY, MEMORY_FILE, MEMORY_HEADER, SECRET_WORDS

def load_memory(path=None):
    """Đọc lại file mỗi lần dùng, để chỗ người dùng tự sửa/xoá trong file có tác dụng ngay."""
    try:
        lines = (path or MEMORY_FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [s.strip() for s in lines if s.strip() and not s.startswith("#")][-MAX_MEMORY:]


# chuyện chỉ đúng lúc này (vừa hỏi, đang đọc / sửa lỗi...): model hay ghi nhầm thành ký ức lâu dài, rồi lần nào nói
# chuyện cũng lôi ra (ký ức từng đầy "Hùng vừa hỏi về local model..." nên câu nào cũng xoay quanh Ollama)
TEMPORARY = re.compile(r"\b(vừa|mới hỏi|just|currently|right now)\b|\bđang (hỏi|tìm hiểu|đọc|xem|code|giải quyết|sửa|gặp"
                       r"|cố|thử|làm bài|tập trung)|\bis (asking|reading|looking|trying|fixing|working on|learning about)",
                       re.IGNORECASE)


def _words(fact):
    return set(re.findall(r"\w+", fact.lower())) - {"bạn", "người", "dùng", "của", "là", "the", "user", "is"}


def _similar(a, b):
    """Hai điều gần như cùng ý (nói khác chữ): "Bạn tên là Hùng" ~ "Tên của người dùng là Hùng"."""
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.6


def remember(facts, path=None):
    """Thêm điều mới vào file: bỏ trùng (kể cả cùng ý khác chữ), bỏ chuyện tạm thời lúc này, bỏ thứ bí mật (mật khẩu,
    dãy số dài như số tài khoản/số thẻ), giữ MAX_MEMORY điều mới nhất. Trả về danh sách điều thật sự được thêm."""
    path = path or MEMORY_FILE
    memory = load_memory(path)
    new = []
    for f in facts:
        if (any(_similar(f, m) for m in memory + new) or TEMPORARY.search(f) or any(w in f.lower() for w in SECRET_WORDS)
                or re.search(r"\d{8,}", f.replace(" ", "").replace(".", "").replace("-", ""))):
            continue
        new.append(f)
    if new:
        try:
            path.write_text(MEMORY_HEADER + "\n".join((memory + new)[-MAX_MEMORY:]) + "\n", encoding="utf-8")
        except OSError as e:  # file đang bị khoá: lần sau nhớ lại
            print("Không ghi được ký ức:", repr(e), file=sys.stderr)
            return []
    return new


LIKE = re.compile(r"^(?:\w+\s+)?(?:rất\s+|really\s+)?(?:yêu thích|thích|mê|ghiền|yêu|likes?|loves?|enjoys?)\s+(.+)$",
                  re.IGNORECASE)
CORE = re.compile(r"\b(tên|thích|ghét|mê|sinh nhật|name|like|love|hate|birthday)\b", re.IGNORECASE)
STOP = {"bạn", "mình", "người", "dùng", "của", "là", "và", "có", "không", "với", "cho", "này", "đó", "the", "user", "and",
        "you", "what", "gì", "thì", "rất", "một", "những", "các"}


def likes(memory):
    """Thứ người dùng thích, lấy từ ký ức: "Thích bún bò" / "Hùng thích nghe nhạc" -> ["bún bò", "nghe nhạc"]."""
    out = []
    for fact in memory:
        m = LIKE.match(fact.strip(" ."))
        if m and not re.search(r"\b(không|chẳng|don't|not)\b", fact[:m.start(1)], re.IGNORECASE):
            out.append(m.group(1))
    return out


def favorite_food(memory):
    """Món ăn người dùng thích -> (tên món, emoji), không có thì None. "Thích ăn bún bò" -> ("bún bò", "🍜")."""
    for thing in likes(memory):
        food = re.sub(r"^(ăn|uống|eating|to eat)\s+", "", thing, flags=re.IGNORECASE)
        key = max((k for k in FOOD_EMOJI if k in food.lower()), key=len, default=None)
        if key:
            return food, FOOD_EMOJI[key]
    return None


def relevant(memory, text=""):
    """Ký ức đáng gửi cho model: tên, thích / ghét, sinh nhật, và điều có chữ trùng với câu đang nói (text). Gửi hết thì
    vài dòng lạc đề kéo câu nào cũng về một chuyện (từng toàn nói Ollama)."""
    words = set(re.findall(r"\w{3,}", text.lower())) - STOP
    return [f for f in memory if CORE.search(f) or words & (set(re.findall(r"\w{3,}", f.lower())) - STOP)]


def log_line(kind, emote, line, path=LOG_FILE):
    """Ghi một dòng, các cột cách nhau bằng tab, để sau đọc lại xem model chọn emote có hợp không."""
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{kind}\t{emote}\t{' '.join(line.split())}\n")
    except OSError as e:  # file đang bị khoá (OneDrive đồng bộ...): bỏ dòng này, đừng làm treo nhân vật
        print("Không ghi được nhật ký:", repr(e), file=sys.stderr)
