"""Kéo màu tóc một ảnh về đúng màu tóc ảnh ngủ (253,141,127), giữ nét sợi và bóng (nén 30%).
Chỉ đổi tóc: sừng (đậm màu hơn), mắt, kẹp, hiệu ứng nhỏ rời không bị đụng.
Chạy: python match_hair.py <ảnh_vào> <ảnh_ra>
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

TARGET = np.array([253, 141, 127], np.float32)  # màu tóc đo từ ảnh ngủ


def hair_mask(im):
    hsv = np.asarray(im.convert("HSV")).astype(int)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    red = ((h <= 12) | (h >= 245)) & (s < 175)  # sừng đỏ đậm màu hơn tóc (độ bão hòa ~190+) -> loại
    core = ndimage.binary_opening(red & (s > 70) & (v > 190), iterations=2)
    lab, n = ndimage.label(core)
    sizes = ndimage.sum(core, lab, range(1, n + 1))
    core = np.isin(lab, np.flatnonzero(sizes > 0.05 * sizes.max()) + 1)  # bỏ mây hơi/dấu nhỏ rời
    shade = ndimage.binary_opening(red & (s > 70) & (v > 140) & (v <= 190), iterations=2)
    return core | (shade & ndimage.binary_dilation(core, iterations=4)), core


def match(im):
    f = np.asarray(im).astype(np.float32)
    whole, core = hair_mask(im)
    f[whole] = TARGET + (f[whole] - np.median(f[core], axis=0)) * 0.7
    w = ndimage.gaussian_filter(whole.astype(np.float32), 1)[..., None]  # mép chuyển mềm
    out = np.asarray(im).astype(np.float32) * (1 - w) + np.clip(f, 0, 255) * w
    return Image.fromarray(out.round().astype(np.uint8))


if __name__ == "__main__":
    src, dst = sys.argv[1:3]
    im = Image.open(src).convert("RGB")
    res = match(im)
    res.save(dst)
    for name, x in (("truoc", im), ("sau", res)):
        _, c = hair_mask(x)
        print(name, np.median(np.asarray(x)[c], axis=0).astype(int))
