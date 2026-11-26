"""desktop: đọc được pin, mạng, thời gian rời máy, cửa sổ đang mở từ Windows, đúng kiểu."""
from claude_chan.desktop import active_title, clipboard_image_seq, battery, fullscreen, idle_seconds, now_playing, online, screenshot_keys

pct, plugged = battery()
assert (pct is None or 0 <= pct <= 100) and isinstance(plugged, bool) and isinstance(online(), bool)
assert 0 <= idle_seconds() < 49 * 24 * 3600  # không âm
assert isinstance(active_title(), str) and isinstance(fullscreen(), bool) and isinstance(screenshot_keys(), bool)
playing = now_playing()  # đang phát gì theo Windows: None hoặc (tên, ca sĩ / kênh, app)
assert playing is None or (len(playing) == 3 and all(isinstance(x, str) for x in playing))
seq, has_image = clipboard_image_seq()
assert isinstance(seq, int) and isinstance(has_image, bool)
