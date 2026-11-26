"""character: đường chuyển động theo cảm xúc luôn kết thúc ở chỗ cũ, mặt quay lại bình thường."""
from claude_chan.character import motion, rubbed, spun
from claude_chan.core.config import EMOTES

for e in EMOTES:
    path = motion(e)
    assert path[-1] == (0, 0, 0) and all(len(p) == 3 and p[2] in (0, 1) for p in path), e
assert any(p[2] for p in motion("co_vu")) and any(p[2] for p in motion("gian_doi"))  # vẫy lightstick, quay ngoắt
cheer = motion("co_vu")  # cổ vũ theo nhịp: lật đúng mỗi 30 khung (0.5s), chạm đất ngay lúc lật
flips = [i for i in range(1, len(cheer) - 1) if cheer[i][2] != cheer[i - 1][2]]
assert flips == [30, 60, 90] and all(cheer[i][1] == 0 for i in flips)
assert max(p[1] for p in motion("lap_lanh")) > max(p[1] for p in motion("mim_cuoi"))  # vui thì nhảy cao hơn

# bị cầm quay vòng / lắc nhiều thì chóng mặt; kéo thẳng một đường dài hay lắc nhẹ thì không
import math
circle = [(i / 60, 600 + 200 * math.cos(i / 6), 400 + 200 * math.sin(i / 6)) for i in range(180)]  # ~4.8 vòng trong 3s
shake = [(i / 60, 600 + 250 * math.sin(i / 4), 400) for i in range(180)]  # lắc ngang mạnh
straight = [(i / 60, 100 + i * 25, 400) for i in range(180)]  # kéo một đường 4500px
wiggle = [(i / 60, 600 + 10 * math.sin(i), 400) for i in range(180)]  # rung tay nhẹ
assert spun(circle) and spun(shake) and not spun(straight) and not spun(wiggle) and not spun([])

# xoa đầu: rê qua lại 4 lượt dài thì tính; rê chuột tí, lướt ngang một đường, lắc ngắn dưới 40px thì không
rub = [(i / 30, 100 + 60 * math.sin(i / 3)) for i in range(60)]  # qua lại biên độ 120px, ~3 vòng trong 2s
tiny = [(i / 30, 100 + 15 * math.sin(i / 3)) for i in range(60)]  # rê chuột tí
across = [(i / 30, 20 + i * 4) for i in range(60)]  # lướt ngang qua đầu
twice = [(i / 30, 100 + 60 * math.sin(i / 6)) for i in range(20)]  # qua lại 1-2 lượt rồi thôi
assert rubbed(rub) and not rubbed(tiny) and not rubbed(across) and not rubbed(twice) and not rubbed([])
