"""Đọc thông tin từ Windows: cửa sổ đang mở, rời máy bao lâu, pin, mạng, cửa sổ toàn màn hình."""
import ctypes


def active_title():
    u = ctypes.windll.user32
    u.GetForegroundWindow.restype = ctypes.c_void_p
    buf = ctypes.create_unicode_buffer(512)
    u.GetWindowTextW(ctypes.c_void_p(u.GetForegroundWindow()), buf, 512)
    return buf.value


def idle_seconds():
    """Số giây từ lần cuối người dùng chạm chuột hoặc bàn phím (Windows tự đếm)."""
    class LastInput(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    info = LastInput(ctypes.sizeof(LastInput))
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
    return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000  # & : bộ đếm quay vòng sau 49 ngày


def clipboard_image_seq():
    """Số đếm thay đổi clipboard của Windows, và clipboard đang chứa ảnh không (vừa chụp màn hình thì có ảnh)."""
    u = ctypes.windll.user32
    return u.GetClipboardSequenceNumber(), bool(u.IsClipboardFormatAvailable(8) or u.IsClipboardFormatAvailable(2))


def clipboard_image():
    """Ảnh đang nằm trong clipboard (vừa chụp màn hình), không có thì None."""
    from PIL import Image, ImageGrab
    try:
        img = ImageGrab.grabclipboard()
    except OSError:  # app khác đang giữ clipboard
        return None
    return img if isinstance(img, Image.Image) else None


def screenshot_keys():
    """Vừa bấm phím chụp màn hình chưa: PrtSc, hoặc Win+Shift+S (công cụ cắt màn hình). Hỏi trạng thái phím của Windows,
    không móc bàn phím. Bit 1 = đã bấm kể từ lần hỏi trước: PrtSc thường chỉ báo nhả phím nên phải dựa vào bit này."""
    k = ctypes.windll.user32.GetAsyncKeyState
    down = lambda vk: k(vk) & 0x8000  # noqa: E731
    return bool(k(0x2C) & 0x8001 or ((down(0x5B) or down(0x5C)) and down(0x10) and down(0x53)))


_drop_hooks = []  # giữ hàm hook sống mãi: bị dọn rác thì Windows gọi vào hàm đã mất, chương trình sập


def accept_drops(*hwnds):
    """Cho kéo thả file từ Explorer vào các cửa sổ hwnds. Trả về list: mỗi lần thả thêm một
    [đường dẫn]; vòng lặp giao diện tự lấy ra xử lý. Bắt WM_DROPFILES bằng hook hàng đợi thông điệp của luồng này
    (không thay hàm xử lý cửa sổ của Tk: gọi lại vào Tk từ hàm Python gắn vào cửa sổ làm Python sập), và trong hook
    không gọi gì vào Tk, chỉ ghi lại đường dẫn."""
    u, sh, k32 = ctypes.windll.user32, ctypes.windll.shell32, ctypes.windll.kernel32
    hook_t = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p)
    u.SetWindowsHookExW.argtypes = [ctypes.c_int, hook_t, ctypes.c_void_p, ctypes.c_uint]
    u.SetWindowsHookExW.restype = ctypes.c_void_p
    u.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p]
    u.CallNextHookEx.restype = ctypes.c_ssize_t
    sh.DragQueryFileW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
    sh.DragQueryFileW.restype = ctypes.c_uint
    sh.DragFinish.argtypes = [ctypes.c_void_p]

    class Msg(ctypes.Structure):
        _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint), ("wParam", ctypes.c_size_t),
                    ("lParam", ctypes.c_ssize_t), ("time", ctypes.c_uint), ("x", ctypes.c_long), ("y", ctypes.c_long)]

    dropped = []

    def hook(code, removing, lp):
        m = ctypes.cast(lp, ctypes.POINTER(Msg)).contents if lp else None
        if code >= 0 and removing and m and m.message == 0x233:  # PM_REMOVE + WM_DROPFILES
            h = ctypes.c_void_p(m.wParam)
            paths = []
            for i in range(sh.DragQueryFileW(h, 0xFFFFFFFF, None, 0)):
                buf = ctypes.create_unicode_buffer(sh.DragQueryFileW(h, i, None, 0) + 1)
                sh.DragQueryFileW(h, i, buf, len(buf))
                paths.append(buf.value)
            sh.DragFinish(h)
            m.message = 0  # WM_NULL: Tk nhận được thì bỏ qua
            dropped.append(paths)
        return u.CallNextHookEx(None, code, removing, lp)

    cb = hook_t(hook)
    _drop_hooks.append(cb)
    u.SetWindowsHookExW(3, cb, None, k32.GetCurrentThreadId())  # 3: WH_GETMESSAGE, chỉ luồng giao diện này
    for h in hwnds:
        sh.DragAcceptFiles(ctypes.c_void_p(h), True)
    return dropped


def battery():
    """(phần trăm pin, đang cắm sạc); máy bàn / không đọc được thì (None, True)."""
    class PowerStatus(ctypes.Structure):
        _fields_ = [("ac", ctypes.c_ubyte), ("flag", ctypes.c_ubyte), ("percent", ctypes.c_ubyte),
                    ("saver", ctypes.c_ubyte), ("life", ctypes.c_ulong), ("full", ctypes.c_ulong)]
    s = PowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)) or s.percent == 255 or s.flag & 128:
        return None, True  # 255 = không rõ, flag 128 = không có pin
    return s.percent, s.ac == 1


def online():
    """Windows có đang báo có mạng không (chỉ hỏi Windows, không gửi gì ra ngoài)."""
    flags = ctypes.c_ulong()
    return bool(ctypes.windll.wininet.InternetGetConnectedState(ctypes.byref(flags), 0))


def window_rect(hwnd):
    """(trái, trên, phải, dưới) đúng phần nhìn thấy của cửa sổ (bỏ viền bóng đổ), hoặc None nếu cửa sổ đã đóng /
    ẩn / thu nhỏ / phóng to hết cỡ / bị Windows giấu (cửa sổ app nền, desktop ảo khác)."""
    u, h = ctypes.windll.user32, ctypes.c_void_p(hwnd)
    if not u.IsWindow(h) or not u.IsWindowVisible(h) or u.IsIconic(h) or u.IsZoomed(h):
        return None
    cloaked = ctypes.c_int()
    ctypes.windll.dwmapi.DwmGetWindowAttribute(h, 14, ctypes.byref(cloaked), 4)  # DWMWA_CLOAKED
    r = (ctypes.c_long * 4)()
    if cloaked.value or ctypes.windll.dwmapi.DwmGetWindowAttribute(h, 9, r, ctypes.sizeof(r)):  # DWMWA_EXTENDED_FRAME_BOUNDS
        return None
    return (r[0], r[1], r[2], r[3]) if r[2] - r[0] > 50 and r[3] - r[1] > 50 else None


def windows():
    """Các cửa sổ app đang mở, trên cùng trước: [(hwnd, (trái, trên, phải, dưới))]. Bỏ cửa sổ của chính chương trình
    này, cửa sổ công cụ / không tiêu đề, và những cái window_rect trả None."""
    import os
    u, found, me = ctypes.windll.user32, [], os.getpid()
    proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def each(h, _):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(ctypes.c_void_p(h), ctypes.byref(pid))
        if (pid.value != me and u.GetWindowTextLengthW(ctypes.c_void_p(h))
                and not u.GetWindowLongW(ctypes.c_void_p(h), -20) & 0x80):  # WS_EX_TOOLWINDOW
            rect = window_rect(h)
            if rect:
                found.append((h, rect))
        return True

    u.EnumWindows(proc(each), 0)
    return found


def fullscreen():
    """Cửa sổ phía trước phủ kín màn hình (game, video toàn màn hình), không tính màn hình nền desktop."""
    u = ctypes.windll.user32
    u.GetForegroundWindow.restype = ctypes.c_void_p
    h = ctypes.c_void_p(u.GetForegroundWindow())
    cls = ctypes.create_unicode_buffer(64)
    u.GetClassNameW(h, cls, 64)
    r = (ctypes.c_long * 4)()
    if cls.value in ("Progman", "WorkerW") or not u.GetWindowRect(h, r):
        return False
    return r[0] <= 0 and r[1] <= 0 and r[2] >= u.GetSystemMetrics(0) and r[3] >= u.GetSystemMetrics(1)


def now_playing():
    """(tên bài / video, ca sĩ / kênh, app) đang PHÁT theo Windows (bảng nhạc hiện khi bấm phím âm lượng: Spotify,
    YouTube trên Chrome / Edge, Apple Music, VLC...), không có gì đang phát thì None. Thiếu gói winrt thì đoán qua
    tên cửa sổ Spotify ("Ca sĩ - Tên bài" khi đang phát). Chạy ở luồng phụ: mỗi lần hỏi mất vài chục ms."""
    try:
        import asyncio
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
    except ImportError:
        return _spotify_title()

    async def ask():
        manager = await Manager.request_async()
        for session in manager.get_sessions():
            if int(session.get_playback_info().playback_status) == 4:  # 4 = đang phát (3 = tạm dừng)
                props = await session.try_get_media_properties_async()
                return props.title or "", props.artist or "", session.source_app_user_model_id or ""
        return None

    try:
        return asyncio.run(ask())
    except OSError:  # dịch vụ nhạc của Windows chưa sẵn sàng / bị tắt
        return None


def _spotify_title():
    """Cửa sổ Spotify có tên "Ca sĩ - Tên bài" khi đang phát (lúc dừng chỉ là "Spotify")."""
    import os
    u, k32, found = ctypes.windll.user32, ctypes.windll.kernel32, []
    proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def each(h, _):
        title = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ctypes.c_void_p(h), title, 256)
        if " - " in title.value:
            pid = ctypes.c_ulong()
            u.GetWindowThreadProcessId(ctypes.c_void_p(h), ctypes.byref(pid))
            handle = k32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
            if handle:
                exe, size = ctypes.create_unicode_buffer(512), ctypes.c_ulong(512)
                if k32.QueryFullProcessImageNameW(handle, 0, exe, ctypes.byref(size)) and \
                        os.path.basename(exe.value).lower() == "spotify.exe":
                    artist, _, song = title.value.partition(" - ")
                    found.append((song, artist, "Spotify"))
                k32.CloseHandle(handle)
        return not found

    u.EnumWindows(proc(each), 0)
    return found[0] if found else None
