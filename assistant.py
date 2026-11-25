"""Trợ lý màn hình: cứ INTERVAL giây chụp màn hình, gửi model vision chạy trên Mac (Ollama qua Tailscale),
rồi hiện emote + lời nói ở góc phải dưới.
Chạy:       python assistant.py
Thử giao diện không cần Mac:  python assistant.py --mock
Bấm chuột trái vào nhân vật: tạm dừng / tiếp tục nhìn màn hình.  Bấm đúp: hỏi nhân vật.
Giữ chuột trái và kéo: di chuyển.  Chuột phải: ẩn xuống khay (bấm icon ở khay để hiện lại, thoát trong menu khay).
Những điều nhân vật nhớ về bạn nằm trong ky_uc.txt (cùng thư mục), sửa hoặc xoá thoải mái.
"""
import ctypes
import sys

from config import TITLE
from ui import main

if __name__ == "__main__":
    # Chỉ chạy một bản: bấm shortcut khi bản tự chạy lúc bật máy đang chạy thì báo, khỏi mở nhân vật thứ hai chồng lên.
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = ctypes.c_void_p
    single = k32.CreateMutexW(None, False, "TroLyManHinh_ClaudeChan")  # giữ tới khi thoát chương trình
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(None, "Claude-chan đang chạy rồi nè!\nBấm icon ở khay hệ thống (cạnh đồng hồ) để hiện.",
                                         TITLE, 0x40)
        sys.exit()
    main()
