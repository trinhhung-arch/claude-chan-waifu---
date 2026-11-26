"""memory: ký ức (thêm, bỏ trùng, bỏ bí mật, giới hạn), nhật ký."""
import tempfile
from pathlib import Path

from claude_chan import memory
from claude_chan.core.config import MAX_MEMORY
from claude_chan.memory import load_memory, log_line, remember

saved = memory.MEMORY_FILE
memory.MEMORY_FILE = Path(tempfile.mkdtemp()) / "ky_uc.txt"  # test không đụng ký ức thật của bạn
try:
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
finally:
    memory.MEMORY_FILE = saved

# nhật ký: mỗi câu một dòng, 4 cột tab; câu nhiều dòng/tab bị gộp thành một dòng
with tempfile.TemporaryDirectory() as d:
    log = Path(d) / "nhat_ky.txt"
    log_line("bình luận", "soc", "Lỗi đỏ kìa!\nSửa đi\tnha", path=log)
    log_line("trả lời", "mot_sach", "Dòng 12 thiếu dấu ngoặc.", path=log)
    rows = [r.split("\t") for r in log.read_text(encoding="utf-8").splitlines()]
    assert [r[1:] for r in rows] == [["bình luận", "soc", "Lỗi đỏ kìa! Sửa đi nha"], ["trả lời", "mot_sach", "Dòng 12 thiếu dấu ngoặc."]]
    assert len(rows[0][0]) == 19  # 2026-11-25 01:20:33
log_line("x", "y", "z", path=Path(d) / "khong_ton_tai" / "a.txt")  # thư mục không có: không được làm sập
