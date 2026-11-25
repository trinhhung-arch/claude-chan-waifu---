"""Ký ức lâu dài (ky_uc.txt) và nhật ký câu nói (nhat_ky.txt)."""
import re
import sys
import time

from config import LOG_FILE, MAX_MEMORY, MEMORY_FILE, MEMORY_HEADER, SECRET_WORDS

def load_memory(path=None):
    """Đọc lại file mỗi lần dùng, để chỗ người dùng tự sửa/xoá trong file có tác dụng ngay."""
    try:
        lines = (path or MEMORY_FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [s.strip() for s in lines if s.strip() and not s.startswith("#")][-MAX_MEMORY:]


def remember(facts, path=None):
    """Thêm điều mới vào file: bỏ trùng, bỏ thứ bí mật (mật khẩu, dãy số dài như số tài khoản/số thẻ),
    giữ MAX_MEMORY điều mới nhất. Trả về danh sách điều thật sự được thêm."""
    path = path or MEMORY_FILE
    memory = load_memory(path)
    new = [f for f in dict.fromkeys(facts) if f not in memory and not any(w in f.lower() for w in SECRET_WORDS)
           and not re.search(r"\d{8,}", f.replace(" ", "").replace(".", "").replace("-", ""))]
    if new:
        try:
            path.write_text(MEMORY_HEADER + "\n".join((memory + new)[-MAX_MEMORY:]) + "\n", encoding="utf-8")
        except OSError as e:  # file đang bị khoá: lần sau nhớ lại
            print("Không ghi được ký ức:", repr(e), file=sys.stderr)
            return []
    return new


def log_line(kind, emote, line, path=LOG_FILE):
    """Ghi một dòng, các cột cách nhau bằng tab, để sau đọc lại xem model chọn emote có hợp không."""
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{kind}\t{emote}\t{' '.join(line.split())}\n")
    except OSError as e:  # file đang bị khoá (OneDrive đồng bộ...): bỏ dòng này, đừng làm treo nhân vật
        print("Không ghi được nhật ký:", repr(e), file=sys.stderr)
