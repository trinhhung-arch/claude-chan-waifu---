"""behaviors: loại app theo tiêu đề cửa sổ."""
from claude_chan.behaviors import app_category, is_music, on_youtube, song_name

assert app_category("assistant.py - waifu claude - Visual Studio Code") == "code"
assert app_category("Steam") == "game" and app_category("Zalo") == "chat" and app_category("Discord | #general") == "chat"
assert app_category("Slay the Spire 2", is_fullscreen=True) == "game"  # game toàn màn hình
assert app_category("Funny cats - YouTube - Google Chrome", is_fullscreen=True) is None  # video trình duyệt: không phải game
assert app_category("Slay the Spire 2") is None and app_category("") is None

# nhạc: app nghe nhạc thì luôn là nhạc; trình duyệt thì tên phải có dấu hiệu bài hát
assert is_music(("Blinding Lights", "The Weeknd", "Spotify.exe")) and is_music(("Lofi beats to study", "Lofi Girl", "Chrome"))
assert is_music(("Firefly Wedding Opening FULL『PERIOD』by iri | Lyrics (Kan/Rom/Eng)", "MAFUYU", "Chrome"))
assert not is_music(("Hướng dẫn nấu phở", "Bếp Nhà", "Chrome")) and not is_music(None)
assert song_name("Firefly Wedding Opening FULL『PERIOD』by iri | Lyrics (Kan/Rom/Eng)") == "Firefly Wedding Opening FULL"
assert song_name("Shape of You (Official Music Video)") == "Shape of You" and len(song_name("a" * 80)) == 41

# nhún theo nhạc chỉ khi đang mở tab YouTube
assert on_youtube("Lofi beats - YouTube - Google Chrome") and on_youtube("YouTube Music")
assert not on_youtube("Spotify Premium") and not on_youtube("main.py - Visual Studio Code")
