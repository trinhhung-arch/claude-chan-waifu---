"""Thay kẹp tóc (logo) ở mọi ảnh bằng một mẫu chuẩn, giữ đúng vị trí, cỡ, góc nghiêng.
Chạy: python fix_logo.py <thư_mục_vào> <thư_mục_ra>
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

# shortcut: tâm kẹp tóc đo tay cho đúng bộ ảnh hiện tại (1254px); thêm ảnh mới thì thêm tâm vào đây
CENTERS = {1: (345, 450), 2: (345, 415), 3: (370, 470), 4: (380, 450), 5: (345, 450), 6: (340, 420),
           7: (470, 490), 8: (300, 420), 9: (345, 460), 10: (375, 410), 11: (375, 515), 12: (380, 425),
           13: (382, 462), 14: (310, 215), 15: (390, 420), 16: (360, 445), 17: (380, 500)}
KEEP = {15}  # giữ kẹp gốc: mắt "><" ăn theo biểu cảm há miệng ngạc nhiên
WIN = 170  # nửa cạnh cửa sổ tìm kẹp quanh tâm
OUTLINE = 9  # độ dày viền nâu quanh kẹp (px)


def clip_fill(rgb, center):
    """Mặt nạ phần thân cam của kẹp (đã lấp lỗ mắt): cam đậm hơn tóc (hue tóc ~6°, kẹp ~15-35°)."""
    hsv = np.asarray(Image.fromarray(rgb).convert("HSV")).astype(int)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    fill = find((h >= 9) & (h <= 26) & (s > 80) & (v > 130), center)
    if fill is None or fill.sum() < 3000:
        # kẹp màu cá hồi gần trùng hue tóc (ảnh ác quỷ): phân biệt bằng độ sáng
        fill = find((h >= 4) & (h <= 14) & (s > 90) & (v > 235), center)
    if fill is None:
        raise ValueError(f"không thấy kẹp quanh {center}")
    return fill


def find(m, center):
    """Khối màu kẹp gần tâm nhất trong cửa sổ, đã lấp lỗ mắt; None nếu không có."""
    cx, cy = center
    win = np.zeros_like(m)
    win[max(cy - WIN, 0):cy + WIN, max(cx - WIN, 0):cx + WIN] = True
    lab, n = ndimage.label(m & win)
    if n == 0:
        return None
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    cents = ndimage.center_of_mass(m, lab, range(1, n + 1))
    # khối đủ lớn gần tâm nhất (tránh bắt nhầm mắt màu hổ phách)
    score = [np.hypot(c[1] - cx, c[0] - cy) if sz > 1500 else 1e9 for sz, c in zip(sizes, cents)]
    if min(score) == 1e9:
        return None
    k = int(np.argmin(score)) + 1
    return ndimage.binary_fill_holes(ndimage.binary_closing(lab == k, iterations=3))


def angle(mask):
    """Góc nghiêng theo hướng các cạnh thẳng của kẹp (hình pixel nên cạnh vuông góc nhau), y hướng xuống."""
    m = ndimage.gaussian_filter(mask.astype(np.float32), 1.5)
    gx, gy = ndimage.sobel(m, axis=1), ndimage.sobel(m, axis=0)
    w = np.hypot(gx, gy)
    th = np.arctan2(gy, gx) * 4  # gấp 4 lần: các cạnh lệch nhau 90° chồng lên cùng một hướng
    a = np.degrees(np.arctan2((w * np.sin(th)).sum(), (w * np.cos(th)).sum())) / 4
    return a  # trong (-45, 45]


def inpaint(rgb, mask, iters=400):
    """Xoá kẹp cũ: khuếch tán màu tóc xung quanh vào vùng mask."""
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = max(ys.min() - 20, 0), ys.max() + 20, max(xs.min() - 20, 0), xs.max() + 20
    crop = rgb[y0:y1, x0:x1].astype(np.float32)
    m = mask[y0:y1, x0:x1]
    for _ in range(iters):
        blur = ndimage.uniform_filter(crop, size=(5, 5, 1))
        crop[m] = blur[m]
    out = rgb.copy()
    out[y0:y1, x0:x1] = crop.round().astype(np.uint8)
    return hair_fill(out, rgb, mask)


def march(src, m, py, px, d, reach):
    """Từ mỗi điểm (py, px) trong vùng xoá m, đi theo hướng d ra hai phía tới pixel đầu tiên ngoài vùng xoá:
    trả về màu và khoảng cách ở mỗi phía (inf nếu không tới được trong tầm reach)."""
    hit = []
    for sgn in (1, -1):
        col = np.zeros((len(py), 3), np.float32)
        dist = np.full(len(py), np.inf, np.float32)
        todo = np.ones(len(py), bool)
        for s in range(1, reach):
            iy = np.round(py + sgn * s * d[0]).astype(int)
            ix = np.round(px + sgn * s * d[1]).astype(int)
            inb = (iy >= 0) & (iy < m.shape[0]) & (ix >= 0) & (ix < m.shape[1])
            ok = todo & inb
            ok[ok] = ~m[iy[ok], ix[ok]]
            col[ok], dist[ok] = src[iy[ok], ix[ok]], s
            todo &= ~ok & inb
            if not todo.any():
                break
        hit += [col, dist]
    return hit


def hair_fill(base, rgb, mask, reach=260):  # đủ xuyên qua cả kẹp cũ to nhất
    """Lấp theo hướng sợi tóc: tóc là các nét gần song song, nên mỗi điểm trong vùng xoá lấy màu hai đầu
    sợi tóc bên ngoài (đi dọc hướng tóc ra hai phía) rồi nội suy -> nét tóc chạy liền qua chỗ kẹp cũ."""
    ys, xs = np.nonzero(mask)
    y0, x0 = max(ys.min() - reach, 0), max(xs.min() - reach, 0)
    y1, x1 = min(ys.max() + reach, rgb.shape[0]), min(xs.max() + reach, rgb.shape[1])
    src = rgb[y0:y1, x0:x1].astype(np.float32)
    m = mask[y0:y1, x0:x1]
    # hướng tóc quanh kẹp: hướng có gradient yếu nhất (tensor cấu trúc trên dải tóc quanh vùng xoá)
    g = ndimage.gaussian_filter(src.mean(axis=2), 1.0)
    gx, gy = ndimage.sobel(g, axis=1), ndimage.sobel(g, axis=0)
    ring = ndimage.binary_dilation(m, iterations=40) & ~m
    jxx, jyy, jxy = (gx * gx)[ring].sum(), (gy * gy)[ring].sum(), (gx * gy)[ring].sum()
    th = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2  # vuông góc với gradient chủ đạo
    py, px = np.nonzero(m)
    c1, t1, c2, t2 = march(src, m, py, px, np.array([np.sin(th), np.cos(th)]), reach)
    both = np.isfinite(t1) & np.isfinite(t2)
    out = base.copy()
    sub = out[y0:y1, x0:x1].astype(np.float32)
    hair = np.median(src[ring], axis=0)
    # chỉ tìm được một phía (sát mép ảnh...): dùng luôn phía đó, khỏi rơi về lấp loang bị mờ
    for c, t, other in ((c1, t1, t2), (c2, t2, t1)):
        one = np.isfinite(t) & ~np.isfinite(other)
        sub[py[one], px[one]] = c[one]
    a1, a2, s1, s2 = c1[both], c2[both], t1[both], t2[both]
    w = (s2 / (s1 + s2))[:, None]
    mix = a1 * w + a2 * (1 - w)
    # hai đầu là hai vật khác hẳn (tóc vs da mặt): kẹp nằm trên tóc nên lấy phía giống màu tóc quanh kẹp,
    # không trộn thành vệt và không kéo da lên chỗ kẹp cũ
    diff = np.abs(a1 - a2).sum(axis=1) > 120
    pick1 = np.abs(a1 - hair).sum(axis=1) < np.abs(a2 - hair).sum(axis=1)
    # ngoại lệ: phía gần hơn là mảng nhạt màu rộng (khăn voan) -> giữ phía đó để mép khăn không bị tóc lấn;
    # khe da hẹp giữa các lọn tóc (ảnh lè lưỡi) vẫn nhường cho tóc
    hsv = np.asarray(Image.fromarray(src.astype(np.uint8)).convert("HSV")).astype(int)
    pale = (hsv[..., 1] < 70) & (hsv[..., 2] > 200)
    wide = ndimage.grey_dilation(ndimage.distance_transform_edt(pale), size=61) > 30
    d = np.array([np.sin(th), np.cos(th)])
    def hit_wide(t, sgn):
        iy = np.clip(np.round(py[both] + sgn * t * d[0]).astype(int), 0, m.shape[0] - 1)
        ix = np.clip(np.round(px[both] + sgn * t * d[1]).astype(int), 0, m.shape[1] - 1)
        return pale[iy, ix] & wide[iy, ix]
    w1, w2 = hit_wide(s1, 1), hit_wide(s2, -1)
    pick1 = np.where(w1 & (s1 <= s2), True, np.where(w2 & (s2 < s1), False, pick1))
    mix[diff] = np.where(pick1[diff, None], a1[diff], a2[diff])
    sub[py[both], px[both]] = mix
    # chỗ hai đầu khác màu, điểm sát nhau có thể chọn khác phía -> sọc; làm mịn riêng các điểm đó
    sel = np.zeros(m.shape, bool)
    sel[py[both][diff], px[both][diff]] = True
    sel = ndimage.binary_dilation(sel, iterations=2) & m
    smooth = ndimage.median_filter(sub, size=(7, 7, 1))
    sub[sel] = smooth[sel]
    out[y0:y1, x0:x1] = sub.round().astype(np.uint8)
    return out


def clip_region(rgb, fill):
    """Thân kẹp + đúng phần viền nâu tối bao quanh (không lấn thêm tóc)."""
    hsv = np.asarray(Image.fromarray(rgb).convert("HSV")).astype(int)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    # 1) thân đầy đủ: thêm vệt bóng (cam nhạt hoặc trắng) dính vào thân, để góc có bóng không bị khuyết
    gloss = (ndimage.distance_transform_edt(~fill) <= 15) & ~fill & (
        ((h >= 8) & (h <= 30) & (v > 200)) | ((s < 25) & (v > 230)))
    lab, _ = ndimage.label(gloss)
    touch = np.unique(lab[ndimage.binary_dilation(fill, iterations=2) & (lab > 0)])
    body = ndimage.binary_fill_holes(ndimage.binary_closing(fill | np.isin(lab, touch[touch > 0]), iterations=4))
    # 2) viền: nới thân ra đúng độ dày viền nâu đo được -> hình đều, không lẹm góc, không dính tóc
    dist = ndimage.distance_transform_edt(~body)
    dark = (dist > 0) & (dist <= OUTLINE + 5) & (v < 150)
    w = np.percentile(dist[dark], 90) if dark.any() else OUTLINE
    return body | (dist <= w)


def deshadow(rgb, region):
    """Bóng đổ của kẹp cũ: thay vì xoá rồi lấp (bị mờ), làm sáng nó lên bằng tóc xung quanh — giữ nguyên nét
    sợi tóc bên dưới. Chỉ tính trong khung quanh kẹp cho nhanh."""
    ys, xs = np.nonzero(region)
    y0, x0 = max(ys.min() - 60, 0), max(xs.min() - 60, 0)
    box = (slice(y0, ys.max() + 60), slice(x0, xs.max() + 60))
    out = rgb.copy()
    out[box] = _deshadow(rgb[box], region[box])
    return out


def _deshadow(rgb, region):
    hsv = np.asarray(Image.fromarray(rgb).convert("HSV")).astype(int)
    v = hsv[..., 2]
    near = ndimage.binary_dilation(region, iterations=22) & ~region  # bóng đổ của kẹp rộng ~15-20px
    ann = ndimage.binary_dilation(region, iterations=45) & ~ndimage.binary_dilation(region, iterations=25)
    dark = near & (v < np.median(v[ann]) - 20)
    dark = ndimage.binary_opening(dark, iterations=3)  # bóng là mảng dày; nét viền/nét tóc mỏng bị loại
    lab, _ = ndimage.label(dark | region)
    ids = np.unique(lab[region])
    zone = ndimage.binary_dilation(np.isin(lab, ids[ids > 0]), iterations=3) & ~region
    # vệt tối sát vật nhạt màu (bóng của khăn voan lên tóc) là nét vẽ thật -> giữ nguyên
    pale = ndimage.binary_opening((hsv[..., 1] < 70) & (v > 200), iterations=2)
    zone &= ~ndimage.binary_dilation(pale, iterations=12)
    if not zone.any():
        return rgb
    f = rgb.astype(np.float32)
    ref = np.median(f[ann], axis=0)
    # độ tối của bóng = màu trung bình mờ (bỏ nét tóc đậm) trong vùng bóng; gain = tóc chuẩn / bóng
    valid = (zone & (f.mean(axis=2) > 0.55 * ref.mean())).astype(np.float32)
    wsum = ndimage.gaussian_filter(valid, 6)
    gain = np.ones_like(f)
    for c in range(3):
        shade = ndimage.gaussian_filter(f[..., c] * valid, 6) / np.maximum(wsum, 1e-3)
        gain[..., c] = np.where(wsum > 0.05, np.clip(ref[c] / np.maximum(shade, 1), 1, 3), 1)
    weight = ndimage.gaussian_filter(zone.astype(np.float32), 2)[..., None]  # mép vùng bóng chuyển mềm
    # chỉ nâng pixel tối lên tối đa bằng màu tóc chuẩn; pixel đã sáng (ánh bóng tóc) giữ nguyên, không bị loá
    lifted = np.maximum(f, np.minimum(f * gain, ref))
    return np.clip(f + (lifted - f) * weight, 0, 255).round().astype(np.uint8)


def make_sprite(rgb, fill):
    """Cắt kẹp mẫu từ ảnh: thân + viền đều, nền trong suốt, khung vuông tâm = trọng tâm thân."""
    full = clip_region(rgb, fill)
    cy, cx = ndimage.center_of_mass(fill)
    ys, xs = np.nonzero(full)
    r = int(max(cx - xs.min(), xs.max() - cx, cy - ys.min(), ys.max() - cy)) + 4
    spr = Image.fromarray(rgb).convert("RGBA")
    spr.putalpha(Image.fromarray(full.astype(np.uint8) * 255))
    return spr.crop((round(cx) - r, round(cy) - r, round(cx) + r, round(cy) + r)), fill.sum(), angle(fill)


def turned(sprite, rot):
    """Phóng x4 rồi quay một lần; thu về cỡ cần dùng ở bước sau -> chỉ một lần làm mềm, mép vẫn sắc."""
    return sprite.resize((sprite.width * 4, sprite.height * 4), Image.LANCZOS).rotate(rot, resample=Image.BICUBIC)


def fit_cover(big, n0, region, cx, cy, target=0.98):
    """Cỡ nhỏ nhất (từ cỡ theo diện tích, tối đa x1.35) để kẹp mới che >= 98% kẹp cũ (cả viền):
    phần tóc phải vẽ lại quanh kẹp còn rất ít, khỏi bị vệt quệt."""
    for n in range(n0, int(n0 * 1.35) + 1, 4):
        spr = big.resize((n, n), Image.LANCZOS)
        a = np.zeros(region.shape, bool)
        x0, y0 = round(cx - n / 2), round(cy - n / 2)
        ys, xs = slice(max(y0, 0), min(y0 + n, region.shape[0])), slice(max(x0, 0), min(x0 + n, region.shape[1]))
        a[ys, xs] = np.asarray(spr.getchannel("A"))[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0] > 128
        if (a & region).sum() >= target * region.sum():
            break
    return spr


def main(src, dst, ref=14):  # 14: kẹp người dùng chọn (ảnh cận mặt), to nhất nên chỉ phải thu nhỏ
    files = {int(p.stem): p for p in Path(src).iterdir() if p.stem.isdigit()}
    ref_rgb = np.asarray(Image.open(files[ref]).convert("RGB"))
    sprite, ref_area, ref_ang = make_sprite(ref_rgb, clip_fill(ref_rgb, CENTERS[ref]))
    Path(dst).mkdir(exist_ok=True)
    for i, f in sorted(files.items()):
        rgb = np.asarray(Image.open(f).convert("RGB"))
        if i in KEEP:
            Image.fromarray(rgb).save(Path(dst) / f"{i}.png")
            print(f"{i}: kept")
            continue
        fill = clip_fill(rgb, CENTERS[i])
        a, area = angle(fill), fill.sum()
        cy, cx = ndimage.center_of_mass(fill)
        region = clip_region(rgb, fill)
        old = ndimage.binary_dilation(region, iterations=8)  # chỉ xoá đúng kẹp cũ (+ viền mờ, viền dày chỗ góc)
        base = Image.fromarray(inpaint(deshadow(rgb, region), old)).convert("RGBA")
        big = turned(sprite, -(a - ref_ang))  # PIL quay ngược chiều kim đồng hồ
        spr = fit_cover(big, round(sprite.width * np.sqrt(area / ref_area)), region, cx, cy)
        base.alpha_composite(spr, (round(cx - spr.width / 2), round(cy - spr.height / 2)))
        base.convert("RGB").save(Path(dst) / f"{i}.png")
        print(f"{i}: angle={a:+.1f} scale={spr.width / sprite.width:.2f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
