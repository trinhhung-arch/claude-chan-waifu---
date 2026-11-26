"""Đường chuyển động theo cảm xúc (thuần tính toán, không đụng Tk)."""
import math


def motion(emote):
    """Đường đi từng khung (~60 khung/giây): (dx, dy lên trên, quay_ngoắt). Mỗi cảm xúc một kiểu:
    vui nhảy 2 nhịp cao, sốc giật nảy rồi rung lắc, buồn chùng xuống rồi từ từ lên, buồn ngủ gật gù 2 cái,
    dỗi quay ngoắt đi rồi quay lại, cổ vũ lật qua lật lại như vẫy lightstick; còn lại nhún 1 nhịp + nảy nhẹ."""
    hop1 = lambda h, n: [(0, h * math.sin(math.pi * i / n), 0) for i in range(n + 1)]
    if emote in ("lap_lanh", "phan_khich"):
        path = hop1(24, 14) + hop1(16, 12)
    elif emote == "co_vu":  # cổ vũ theo nhịp 120 BPM: mỗi nhịp 0.5s nhún bật lên, nghiêng sang một bên, chạm đất đúng
        # nhịp thì lật sang bên kia như vẫy lightstick; 4 nhịp (2s), đang nói thì lặp tiếp
        beat = 30
        path = [(round((4 if b % 2 else -4) * math.sin(math.pi * j / beat)), 16 * math.sin(math.pi * j / beat), b % 2)
                for b in range(4) for j in range(beat)]
    elif emote == "soc":
        path = hop1(14, 8) + [(round(7 * math.sin(i * 1.7) * (1 - i / 24)), 0, 0) for i in range(24)]
    elif emote == "buon":
        path = [(0, -10 * i / 30, 0) for i in range(30)] + [(0, -10, 0)] * 40 + [(0, -10 * (1 - i / 50), 0) for i in range(51)]
    elif emote in ("duoc_xoa", "phe_qua", "bo"):  # được xoa đầu: không nhảy, để hiệu ứng bẹp - nảy / phồng to lo
        path = []
    elif emote in ("buon_ngu", "ngap"):  # buồn ngủ / ngáp: gật gù chậm 2 cái
        path = [(0, -7 * math.sin(math.pi * i / 45) ** 2, 0) for i in range(91)]
    elif emote == "gian_doi":
        path = [(0, 8 * math.sin(math.pi * i / 8), 1) for i in range(9)] + [(0, 0, 1)] * 50 + [(0, 0, 0)]
    else:
        path = hop1(18, 14) + hop1(5, 7)
    return path + [(0, 0, 0)]


SPIN_WINDOW, SPIN_PATH, SPIN_TURNS = 3.0, 3000, 6  # trong 3 giây cuối: tay đi > 3000px và đổi hướng >= 6 lần


def spun(path):
    """Bị cầm quay vòng / lắc qua lắc lại nhiều không: path = [(giây, x, y)] vị trí lúc kéo (đã chỉ giữ SPIN_WINDOW giây
    cuối). Kéo một đường dài thẳng thì đi xa nhưng không đổi hướng; lắc nhẹ thì đổi hướng nhưng không đi xa."""
    length = sum(math.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(path, path[1:]))
    turns = 0
    for axis in (1, 2):  # đếm số lần đổi chiều theo ngang và theo dọc (bỏ qua rung tay dưới 15px)
        anchor, last = path[0][axis] if path else 0, 0
        for p in path[1:]:
            d = p[axis] - anchor
            if abs(d) > 15:
                sign = 1 if d > 0 else -1
                turns += last and sign != last
                last, anchor = sign, p[axis]
            elif last and (p[axis] - anchor) * last > 0:
                anchor = p[axis]
    return length > SPIN_PATH and turns >= SPIN_TURNS


RUB_WINDOW, RUB_STROKE, RUB_TURNS = 2.0, 40, 4  # trong 2 giây cuối: rê qua lại đổi chiều >= 4 lần, mỗi lượt >= 40px


def rubbed(xs):
    """Đang xoa đầu thật hay chỉ lướt / rê chuột tí trên đầu: xs = [(giây, x)] chỗ chuột trên đầu (chỉ giữ RUB_WINDOW
    giây cuối). Xoa = qua lại ít nhất 5 lượt (đổi chiều RUB_TURNS lần), mỗi lượt dài từ RUB_STROKE px."""
    turns, sign, peak = 0, 0, xs[0][1] if xs else 0
    for _, x in xs[1:]:
        if sign and (x - peak) * sign >= 0:
            peak = x  # vẫn đi tiếp chiều cũ
        elif abs(x - peak) >= RUB_STROKE:  # quay đầu đủ xa so với chỗ xa nhất của lượt trước: thêm một lượt
            turns += bool(sign)
            sign, peak = (1 if x > peak else -1), x
    return turns >= RUB_TURNS
