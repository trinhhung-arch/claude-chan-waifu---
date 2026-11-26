"""Claude-chan: cứ INTERVAL giây chụp màn hình, gửi model vision chạy qua Ollama (máy này hoặc máy khác),
rồi hiện emote + lời nói ở góc phải dưới.
Chạy:       python assistant.py
Thử giao diện không cần model:  python assistant.py --mock
Bấm chuột trái vào nhân vật: tạm dừng / tiếp tục nhìn màn hình.  Bấm đúp: hỏi nhân vật.
Giữ chuột trái và kéo: di chuyển.  Chuột phải: ẩn xuống khay (bấm icon ở khay để hiện lại, thoát trong menu khay).
Những điều nhân vật nhớ về bạn nằm trong ky_uc.txt (cùng thư mục), sửa hoặc xoá thoải mái.
"""
import ctypes
import sys
import time

from claude_chan.core.config import OPEN_FLAG, TITLE
from claude_chan.app import main

if __name__ == "__main__":
    # Chỉ chạy một bản. Bấm shortcut lúc đang chạy: nhờ bản đang chạy mở cửa sổ Claude-chan rồi thoát, khỏi mở nhân vật
    # thứ hai chồng lên. --restart (lưu cài đặt xong tự chạy lại): đợi bản cũ thoát hẳn rồi mới chạy.
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = ctypes.c_void_p
    for _ in range(50 if "--restart" in sys.argv else 1):
        single = k32.CreateMutexW(None, False, "TroLyManHinh_ClaudeChan")  # giữ tới khi thoát chương trình
        if ctypes.get_last_error() != 183:  # 183 = ERROR_ALREADY_EXISTS: bản khác đang chạy
            break
        k32.CloseHandle(ctypes.c_void_p(single))
        time.sleep(0.3)
    else:
        if "--restart" in sys.argv:  # bản cũ mãi không thoát: báo thay vì chạy chồng
            ctypes.windll.user32.MessageBoxW(None, "Claude-chan chưa chạy lại được, thử mở lại sau nhé.", TITLE, 0x30)
        else:
            OPEN_FLAG.touch()
        sys.exit()
    main()
